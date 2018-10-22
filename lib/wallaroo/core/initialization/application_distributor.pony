/*

Copyright 2017 The Wallaroo Authors.

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
 implied. See the License for the specific language governing
 permissions and limitations under the License.

*/

use "collections"
use "files"
use "net"
use "wallaroo"
use "wallaroo/core/common"
use "wallaroo/core/grouping"
use "wallaroo/core/invariant"
use "wallaroo/core/messages"
use "wallaroo/core/metrics"
use "wallaroo/core/sink"
use "wallaroo/core/source"
use "wallaroo/core/topology"
use "wallaroo/ent/recovery"
use "wallaroo_labs/dag"
use "wallaroo_labs/messages"
use "wallaroo_labs/mort"
use "wallaroo_labs/thread_count"


actor ApplicationDistributor is Distributor
  let _auth: AmbientAuth
  let _routing_id_gen: RoutingIdGenerator = RoutingIdGenerator
  let _local_topology_initializer: LocalTopologyInitializer
  let _app_name: String
  let _pipeline: BasicPipeline val

  new create(auth: AmbientAuth, app_name: String,
    pipeline: BasicPipeline val,
    local_topology_initializer: LocalTopologyInitializer)
  =>
    _auth = auth
    _local_topology_initializer = local_topology_initializer
    _app_name = app_name
    _pipeline = pipeline

  be distribute(cluster_initializer: (ClusterInitializer | None),
    worker_count: USize, worker_names: Array[String] val,
    initializer_name: String)
  =>
    @printf[I32]("Initializing application\n".cstring())
    _distribute(cluster_initializer, worker_count,
      worker_names, initializer_name)

  be topology_ready() =>
    @printf[I32]("Application has successfully initialized.\n".cstring())

  fun ref _distribute(cluster_initializer: (ClusterInitializer | None),
    worker_count: USize, worker_names: Array[WorkerName] val,
    initializer_name: WorkerName)
  =>
    @printf[I32]("---------------------------------------------------------\n".cstring())
    @printf[I32]("vvvvvv|Initializing Topologies for Workers|vvvvvv\n\n".cstring())

    try
      let all_workers_trn = recover trn Array[WorkerName] end
      all_workers_trn.push(initializer_name)
      for w in worker_names.values() do all_workers_trn.push(w) end
      let all_workers: Array[WorkerName] val = consume all_workers_trn

      // Since a worker doesn't know the specific routing ids of state
      // steps on other workers (it only knows that certain keys are handled
      // by certain workers), we need a more general way to route things
      // like barriers to downstream state steps. To enable this, we create
      // a RoutingId for each (state name, worker name) pair.
      let state_routing_ids =
        recover iso Map[StateName, Map[WorkerName, RoutingId] val] end

      let stateless_partition_routing_ids =
        recover iso Map[RoutingId, Map[WorkerName, RoutingId] val] end

      // Keep track of workers that cannot be removed during shrink to fit.
      // Currently only the initializer has sources, so we just add it here.
      let non_shrinkable = recover trn SetIs[WorkerName] end
      non_shrinkable.set(initializer_name)

      // ASSUMPTION: The only case where a node in the logical graph has more
      // than one output is when it points to multiple sinks.

      let logical_graph = _pipeline.graph()

      //!@
      @printf[I32]("Logical Graph:\n%s\n".cstring(), logical_graph.string().cstring())

      // Traverse graph from sinks to sources, moving any key_by stages back
      // to immediate upstream nodes.
      let interm_graph = Dag[StepInitializer]

      let frontier = Array[U128]
      let processed = SetIs[U128]
      let edges = Map[U128, SetIs[U128]]
      let groupers = Map[U128, (Shuffle | GroupByKey)]

      // Add Wallaroo sinks to intermediate graph
      for sink_node in logical_graph.sinks() do
        match sink_node.value
        | let sb: SinkBuilder =>
          // !@ Passing in app_name for pipeline name
          let egress_builder = EgressBuilder(_app_name, sink_node.id,
            sb)
          interm_graph.add_node(egress_builder, sink_node.id)
        else
          // All sinks in logical graph should be Wallaroo sinks
          Fail()
        end

        for upstream_node in sink_node.ins() do
          let u_id = upstream_node.id

          edges.insert_if_absent(u_id, SetIs[U128])?.set(sink_node.id)
          if not frontier.contains(u_id) then
            frontier.push(u_id)
          end
        end
        processed.set(sink_node.id)
      end

      while frontier.size() > 0 do
        let next_id = frontier.pop()?
        var node = logical_graph.get_node(next_id)?
        if processed.contains(node.id) then continue end
        match node.value
        | let rb: RunnerBuilder =>
          let grouper =
            if groupers.contains(node.id) then
              groupers(node.id)?
            else
              None
            end

          // Create the StepBuilder for this stage. If the stage is a state
          // computation, then we can simply create it. If the stage is
          // a stateless computation, we try to coalesce it onto predecessor
          // stateless computations if we can.
          let s_builder =
            if rb.is_stateful() then
              StepBuilder(_app_name, _app_name, rb,
                node.id, rb.routing_group(), grouper, rb.is_stateful())
            else
              // We are going to try to coalesce this onto the previous
              // node, and continue in this way one predecessor node a time,
              // checking if each is stateless and has only one output.
              // As long as this is true, we continue building a list of
              // runner builders until we come to the earliest one we can
              // coalesce onto. We then use the outputs of the last node
              // in the sequence and the inputs of the earliest one.
              // We create a RunnerSequenceBuilder and pass it into the
              // StepBuilder for this stage.

              // We use this id to route the coalesced computations to the
              // outputs of the last node in the coalesced sequence.
              var output_id = node.id

              // We are building up an array of RunnerBuilders that we will
              // coalesce into a RunnerSequenceBuilder. Each node added after
              // this one must be unshifted (i.e. added to the front), since
              // we are traversing the graph backwards.
              let coalesced_comps = recover iso Array[RunnerBuilder] end
              coalesced_comps.unshift(rb)

              // We will use the parallelism value of the earliest node in
              // the sequence as the parallelism value of the stage.
              var parallelism = rb.parallelism()

              // For each node we try to coalesce onto, we need to check that
              // it has only one input. For now, we can only coalesce a
              // linear pipeline of stateless computations.
              var inputs = Array[DagNode[Stage] val]
              for n in node.ins() do
                inputs.push(n)
              end

              var reached_last_predecessor = false
              while not reached_last_predecessor do
                var should_coalesce = false
                // We only coalesce linear pipelines, so we must make
                // sure we have only one input.
                if inputs.size() == 1 then
                  let i_node = inputs(0)?
                  match i_node.value
                  // We only coalesce computations, so we check if the next
                  // node is a RunnerBuilder.
                  | let i_rb: RunnerBuilder =>
                    // We only coalesce stateless computations.
                    // !@ TODO: There is no longer any reason not to coalesce
                    // these onto a stateful computation and stop there. But
                    // if it's stateful, we shouldn't add its inputs to the
                    // input array.
                    if not i_rb.is_stateful() then
                      should_coalesce = true
                      // We mark this node as done processing since we don't
                      // want to visit it again in the outer while loop
                      // working through frontier.
                      processed.set(node.id)
                      // We set the input as our current node.
                      node = i_node
                      // We put this RunnerBuilder at the front of our
                      // array of coalesced RunnerBuilders.
                      coalesced_comps.unshift(i_rb)
                      // This value will end up being the parallelism of the
                      // first node in the coalesced sequence.
                      parallelism = i_rb.parallelism()
                      // We set inputs to be those of the new current node,
                      // so we can check them on the next iteration.
                      inputs.clear()
                      for i in node.ins() do
                        inputs.push(i)
                      end
                    end
                  end
                end
                if not should_coalesce then
                  reached_last_predecessor = true
                end
              end
              // We need to reroute all outputs from the last node in the
              // coalesced sequence to be outputs from the coalesced node.
              // We do this step by step as we move back through the sequence.
              let outs = edges(output_id)?
              edges.remove(output_id)?
              edges(node.id) = outs
              output_id = node.id

              let new_rb = RunnerSequenceBuilder(consume coalesced_comps,
                parallelism)
              StepBuilder(_app_name, _app_name, new_rb, node.id,
                rb.routing_group(), grouper, rb.is_stateful())
            end

          interm_graph.add_node(s_builder, node.id)

          // If this is part of a step group, assign a special routing id
          // for that group to each worker.
          match s_builder.routing_group()
          | let sn: StateName =>
            let worker_map = recover iso Map[WorkerName, RoutingId] end
            for w in all_workers.values() do
              worker_map(w) = _routing_id_gen()
            end
            state_routing_ids(sn) = consume worker_map
          | let ri: RoutingId =>
            let worker_map = recover iso Map[WorkerName, RoutingId] end
            for w in all_workers.values() do
              worker_map(w) = _routing_id_gen()
            end
            stateless_partition_routing_ids(ri) = consume worker_map
          end

          for i_node in node.ins() do
            // !@ We're parallelizing all computations
            groupers(i_node.id) = Shuffle

            if not frontier.contains(i_node.id) and
              not processed.contains(i_node.id)
            then
              frontier.push(i_node.id)
            else
              // This currently means we've violated our assumption that
              // you can only have multiple outputs to sinks. An input to this
              // non-sink should not have been added to the frontier yet since
              // its only output is to this node.
              Fail()
            end

            // Set edge from this input to us if it's a computation or
            // source
            match i_node.value
            | let input: (RunnerBuilder | SourceConfig) =>
              edges.insert_if_absent(i_node.id, SetIs[U128])?
                .set(node.id)
            end
          end
        | let gbk: GroupByKey =>
          for i_node in node.ins() do
            groupers(i_node.id) = gbk
            // Reroute inputs to our outputs
            for edge_target in node.outs() do
              edges.insert_if_absent(i_node.id, SetIs[U128])?
                .set(edge_target.id)
            end
            if not frontier.contains(i_node.id) and
              not processed.contains(i_node.id)
            then
              frontier.push(i_node.id)
            end
          end
        | let sc: SourceConfig =>
          let grouper =
            if groupers.contains(node.id) then
              groupers(node.id)?
            else
              None
            end
          // !@ Using an empty runner sequence builder since I'm not yet
          // coalescing.
          let r_builder = RunnerSequenceBuilder(
            recover Array[RunnerBuilder] end where parallelism' = 0)
          let source_data = SourceData(node.id, _app_name, r_builder,
            sc.source_listener_builder_builder(), grouper)
          interm_graph.add_node(source_data, node.id)
        else
          // This shouldn't be any other kind
          Fail()
        end
        // Mark this node as done
        processed.set(node.id)
      end

      for (origin, targets) in edges.pairs() do
        for t in targets.values() do
          interm_graph.add_edge(origin, t)?
        end
      end

      let non_shrinkable_to_send = consume val non_shrinkable

      //!@ We have to put values in these!
      let state_routing_ids_to_send = consume val state_routing_ids
      let stateless_partition_routing_ids_to_send =
        consume val stateless_partition_routing_ids

      let initializer_graph = interm_graph.clone()?

      //!@
      @printf[I32]("Initializer Graph:\n%s\n".cstring(), initializer_graph.string().cstring())

      let worker_graph = interm_graph.clone()?

      let other_local_topologies =
        recover iso Map[WorkerName, LocalTopology] end

      for w in all_workers.values() do
        let barrier_source_id = _routing_id_gen()

        let graph_to_send =
          if w == initializer_name then
            initializer_graph
          else
            worker_graph
          end

        let local_topology =
          LocalTopology(_app_name, w, graph_to_send,
            recover Map[U128, SetIs[RoutingId] val] end,
            all_workers, non_shrinkable_to_send, state_routing_ids_to_send,
            stateless_partition_routing_ids_to_send,
            barrier_source_id).assign_routing_ids(_routing_id_gen)

        // If this is the "initializer"'s (i.e. our) turn, then
        // immediately (asynchronously) begin initializing it. If not, add it
        // to the list we'll use to distribute to the other workers
        if w == initializer_name then
          _local_topology_initializer.update_topology(local_topology)
          _local_topology_initializer.initialize(cluster_initializer)
        else
          other_local_topologies(w) = local_topology
        end
      end

      // Distribute the LocalTopologies to the other (non-initializer) workers
      if worker_count > 1 then
        match cluster_initializer
        | let ci: ClusterInitializer =>
          ci.distribute_local_topologies(consume other_local_topologies)
        else
          @printf[I32]("Error distributing local topologies!\n".cstring())
        end
      end
      @printf[I32](("\n^^^^^^|Finished Initializing Topologies for " +
        "Workers|^^^^^^^\n").cstring())
      @printf[I32](("------------------------------------------------------" +
        "---\n").cstring())
    else
      @printf[I32]("Error initializing application!\n".cstring())
      Fail()
    end
