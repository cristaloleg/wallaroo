


# partial: source --> node | merged-partials --> node
# pipeline: partial --> sink/s

# partial interface (built starting from source):
#	- add_next_node: partial
#   - merge_partial: partial
#   - add_sink/s: pipeline


class Partial(object):
	def __init__(self):
		self.partials = Set
		self.tail = [] # sequence of nodes

	def is_empty():
		(len(self.partials) > 0) or (len(self.tail) > 0)

	def add_next_node(self, value):
		self.tail.push(value)
		return self

	def merge(self, partial):
		if not partial.is_empty():
			self.partials.set(partial)
		return self

	def add_sink(self, sink):
		return Pipeline(self.partials, self.tail, sink)

	# Machida Pony sketch (do this recursively through partials)
	# iterate through all partials in a partial
	# 	let pipelines = Array[Pipeline]
	# 	for p in partials.values() do
	# 		let pipe = ...
	# 		pipelines.push(pipe)
	# 	end
	# 	merge all pipelines
	# add sink
	#   big_pipeline.to_sink/s()

# Order: each partial separately, merge, each node in tail
# Partial => .source().../.to()/.merge()
# Pipeline => partial.to_sink()




class LogicalGraph(object):
	def __init__(self):
		self.source_partials = Set



		self.nodes = []
		self.edges = {}
		self.sinks = Set

	def contains(self, idx):
		len(self.nodes) > idx

	def add_node(self, value):
		self.sinks.set(len(self.nodes))
		self.nodes.push(value)

	def add_edge(self, from_idx, to_idx):
		if self.contains(from_idx) and self.contains(to_idx):
			if not self.edges.contains(from_idx):
				self.edges(from_idx) = []

			self.edges[from_idx].push(to_idx)
			if self.sinks.contains(from_idx):
				self.sinks.unset(from_idx)
		else:
			throw Error

  	def merge(self, dag):
  		# map old idxs to new idxs by adding this idx_diff
  		idx_diff = len(self.nodes)

	    for n in dag.nodes:
	    	self.add_node(n)

	    for (k, v) in self.edges:
	    	self.add_edge(from_idx + idx_diff, to_idx + idx_diff)
