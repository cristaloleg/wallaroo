# Copyright 2018 The Wallaroo Authors.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.


import argparse
import pickle
import struct
import inspect
import sys

import wallaroo.experimental


class Unbuffered(object):
   def __init__(self, stream):
       self.stream = stream
   def write(self, data):
       self.stream.write(data)
       self.stream.flush()
   def writelines(self, datas):
       self.stream.writelines(datas)
       self.stream.flush()
   def __getattr__(self, attr):
       return getattr(self.stream, attr)


# If python is running with PIPE stdout/stderr, replace them with
# ones that always flush
if not sys.stdout.isatty():
    sys.stdout = Unbuffered(sys.stdout)
if not sys.stderr.isatty():
    sys.stderr = Unbuffered(sys.stderr)


def serialize(o):
    return pickle.dumps(o)


def deserialize(bs):
    return pickle.loads(bs)

class WallarooParameterError(Exception):
    pass

def source(name, source_config):
    return Pipeline.from_source(name, source_config)

def build_application(app_name, pipeline):
    # pipeline.validate_actions()
    return pipeline.to_tuple(app_name)

class Pipeline(object):
    def __init__(self, pipeline_tree):
        self._pipeline_tree = pipeline_tree

    @classmethod
    def from_source(class_object, name, source_config):
        pipeline_tree = _PipelineTree(("source", name, source_config.to_tuple()))
        return Pipeline(pipeline_tree)

        # !@ We need to improve this when Brian updates connectors API.
        # if isinstance(source_config, str):
        #     (port, decoder) = self._connectors[source_config]
        #     connector = wallaroo.experimental.SourceConnectorConfig(host='localhost', port=port, decoder=decoder)
        #     self._actions.append(("source", name, connector.to_tuple()))
        # else:
        #     self._actions.append(("source", name, source_config.to_tuple()))

    def to_tuple(self, app_name):
        return self._pipeline_tree.to_tuple(app_name)

    def to(self, computation):
        return self.clone().__to__(computation)

    def __to__(self, computation):
        if computation.is_stateful:
            self._pipeline_tree.add_stage(("to_state", computation))
        else:
            self._pipeline_tree.add_stage(("to", computation))
        return self

    def to_sink(self, sink_config):
        return self.clone().__to_sink__(sink_config)

    def __to_sink__(self, sink_config):
        if isinstance(sink_config, str):
            (port, encoder) = self._connectors[sink_config]
            connector = wallaroo.experimental.SinkConnectorConfig(host='localhost', port=port, encoder=encoder)
            self._pipeline_tree.add_stage(("to_sink", connector.to_tuple()))
        else:
            self._pipeline_tree.add_stage(("to_sink", sink_config.to_tuple()))
        return self

    def to_sinks(self, sink_configs):
        return self.clone().__to_sinks__(sink_configs)

    def __to_sinks__(self, sink_configs):
        sinks = []
        for sc in sink_configs:
            if isinstance(sc, str):
                (port, encoder) = self._connectors[sc]
                connector = wallaroo.experimental.SinkConnectorConfig(host='localhost', port=port, encoder=encoder)
                sinks.append(connector.to_tuple())
            else:
                sinks.append(sc.to_tuple())
        self._pipeline_tree.add_stage(("to_sinks", sinks))
        return self

    def key_by(self, key_extractor):
        return self.clone().__key_by__(key_extractor)

    def __key_by__(self, key_extractor):
        self._pipeline_tree.add_stage(("key_by", key_extractor))
        return self

    def merge(self, pipeline):
        return self.clone().__merge__(pipeline.clone())

    def __merge__(self, pipeline):
        self._pipeline_tree.merge(pipeline._pipeline_tree)
        return self

    def clone(self):
        return Pipeline(self._pipeline_tree.clone())

##!@
# class ApplicationBuilder(object):
#     def __init__(self, name):
#         self._connectors = {}
#         self._next_source_connector_port = 7100
#         self._next_sink_connector_port = 7200
#         self._actions = [("name", name)]

#     def source_connector(self, name, encoder, decoder, port=None):
#         port_num = port or self._next_source_connector_port
#         # for lookup in the connector script
#         self._actions.append(("source_connector", name, port_num, encoder, decoder))
#         # for lookup in the pipeline builder
#         self._connectors[name] = (port_num, decoder)
#         self._next_source_connector_port += 1
#         return self

#     def sink_connector(self, name, encoder, decoder, port=None):
#         port_num = port or self._next_sink_connector_port
#         # for lookup in the connector script
#         self._actions.append(("sink_connector", name, port_num, encoder, decoder))
#         # for lookup in the pipeline builder
#         self._connectors[name] = (port_num, encoder)
#         self._next_sink_connector_port += 1
#         return self

#     def done(self):
#         self._actions.append(("done",))
#         return self

#     def build(self):
#         self._validate_actions()
#         return self._actions

#     def _validate_actions(self):
#         self._steps = {}
#         self._pipelines = {}
#         self._states = {}
#         last_action = None
#         has_sink = False
#         # Ensure that we don't add steps unless we are in an unclosed pipeline
#         expect_steps = False

#         for action in self._actions:
#             if action[0][0:2] == "to" and not expect_steps:
#                 if last_action == "to_sink":
#                     raise WallarooParameterError(
#                         "Unable to add a computation step after a sink. "
#                         "Please declare a new pipeline first.")
#                 else:
#                     raise WallarooParameterError(
#                         "Please declare a new pipeline before adding "
#                         "computation steps.")

#             if action[0] == "new_pipeline":
#                 self._validate_unique_pipeline_name(action[1], action[2])
#                 expect_steps = True
#             elif action[0] == "to_state_partition":
#                 self._validate_state(action[2], action[3], action[5])
#                 self._validate_unique_partition_labels(action[5])
#                 self._validate_partition_function(action[4])
#             elif action[0] == "to_stateful":
#                 self._validate_state(action[2], action[3])
#             elif action[0] == "to_sink":
#                 has_sink = True
#                 expect_steps = False

#             last_action = action[0]

#         # After checking all of our actions, we should have seen at least one
#         # pipeline terminated with a sink.
#         if not has_sink:
#             raise WallarooParameterError(
#                 "At least one pipeline must define a sink")

#     def _validate_unique_pipeline_name(self, pipeline, source_config):
#         if pipeline in self._pipelines:
#             raise WallarooParameterError((
#                 "A computation named {0} is defined more than once. "
#                 "Please use unique names for your steps."
#                 ).format(repr(computation.name)))
#         else:
#             self._pipelines[pipeline] = source_config

#     def _validate_state(self, ctor, name, partitions = None):
#         if name in self._states:
#             (other_ctor, other_partitions) = self._states[name]
#             if other_ctor.state_cls != ctor.state_cls:
#                 raise WallarooParameterError((
#                     "A state with the name {0} has already been defined with "
#                     "an different type {1}, instead of {2}."
#                     ).format(repr(name), other_ctor.state_cls, ctor.state_cls))
#             if other_partitions != partitions:
#                 raise WallarooParameterError((
#                     "A state with the name {0} has already been defined with "
#                     "an different paritioning scheme {1}, instead of {2}."
#                     ).format(repr(name), repr(other_partitions), repr(partitions)))
#         else:
#             self._states[name] = (ctor, partitions)

#     def _validate_unique_partition_labels(self, partitions):
#         if type(partitions) != list:
#             raise WallarooParameterError(
#                 "Partitions lists should be of type list. Got a {0} instead."
#                 .format(type(partitions)))
#         if len(set(partitions)) != len(partitions):
#             raise WallarooParameterError(
#                 "Partition labels should be uniquely identified via equality "
#                 "and support hashing. You might have duplicates or objects "
#                 "which can't be used as keys in a dict.")

#     def _validate_partition_function(self, partition_function):
#         if not getattr(partition_function, "partition", None):
#             raise WallarooParameterError(
#                 "Partition function is missing partition method. "
#                 "Did you forget to use the @wallaroo.partition_function "
#                 "decorator?")


def _validate_arity_compatability(obj, arity):
    """
    To assist in proper API use, it's convenient to fail fast with erros as
    soon as possible. We use this function to check things we decorate for
    compatibility with our desired number of arguments.
    """
    if not callable(obj):
        raise WallarooParameterError(
            "Expected a callable object but got a {0}".format(obj))
    spec = inspect.getargspec(obj)
    upper_bound = len(spec.args)
    lower_bound = upper_bound - (len(spec.defaults) if spec.defaults else 0)
    if arity > upper_bound or arity < lower_bound:
        raise WallarooParameterError((
            "Incompatible function arity, your function must allow {0} "
            "arguments."
            ).format(arity))


def attach_to_module(cls, cls_name, func):
    # Do some scope mangling to create a uniquely named class based on
    # the decorated function's name and place it in the wallaroo module's
    # namespace so that pickle can find it.

    name = cls_name + '__' + func.__name__

    # Python2: use __name__
    if sys.version_info.major == 2:
        cls.__name__ = name
    # Python3: use __qualname__
    else:
        cls.__qualname__ = name

    globals()[name] = cls
    return globals()[name]


def _wallaroo_wrap(name, func, base_cls, **kwargs):
    # Case 1: Computations
    if issubclass(base_cls, Computation):
        # Create the appropriate computation signature
        if base_cls._is_state:
            def comp(self, data, state):
            # def comp(data, state):
                return func(data, state)
        else:
            def comp(self, data):
            # def comp(data):
                return func(data)

        # Create a custom class type for the computation
        class C(base_cls):
            __doc__ = func.__doc__
            __module__ = __module__
            def name(self):
                return name

        # Attach the computation to the class
        # TODO: maybe move this to machida, using PyObject_IsInstance
        # instead of PyObject_HasAttrString
        if base_cls._is_multi:
            C.compute_multi = comp
        else:
            C.compute = comp

        if base_cls._is_state:
            initial_state = kwargs['state']
            def build_initial_state(self):
                try:
                    state = initial_state()
                    return state
                except Exception as err:
                    print(err)
                    # What should we do here?

            C.initial_state = build_initial_state
            C.is_stateful = True
        else:
            C.is_stateful = False


    # Case 2: Partition
    elif base_cls is KeyExtractor:
        class C(base_cls):
            def extract_key(self, data):
                res = func(data)
                if isinstance(res, int):
                    return chr(res)
                return res

    # Case 3: Encoder
    elif base_cls is OctetEncoder:
        class C(base_cls):
            def encode(self, data):
                return func(data)

    elif base_cls is ConnectorEncoder:
        class C(base_cls):
            def encode(self, data, partition=None, sequence=None):
                encoded = func(data)
                if partition:
                    part = str(partition).encode('utf-8')
                else:
                    part = b''
                if sequence:
                    seq = int(sequence)
                else:
                    seq = -1
                # struct.calcsize('<q') = 8
                meta = struct.pack('<H{}sq'.format(len(part)), len(part) + 8, part, seq)
                return struct.pack(
                    '<I{}s{}s'.format(len(meta), len(encoded)),
                    len(meta) + len(encoded), meta, encoded)

    # Case 4: Decoder
    elif base_cls is OctetDecoder:
        header_length = kwargs['header_length']
        length_fmt = kwargs['length_fmt']
        class C(base_cls):
            def header_length(self):
                return header_length
            def payload_length(self, bs):
                return struct.unpack(length_fmt, bs)[0]
            def decode(self, bs):
                return func(bs)

    elif base_cls is ConnectorDecoder:
        class C(base_cls):
            def header_length(self):
                # struct.calcsize('<I')
                return 4
            def payload_length(self, bs):
                return struct.unpack("<I", bs)[0]
            def decode(self, bs):
                meta_len = struct.unpack_from('<H', bs)[0]
                # We dropping the metadata on the floor for now, slice out the
                # remaining data for message decoding.
                # struct.calcsize('<H') = 2
                message_data = bs[2 + meta_len :]
                return func(message_data)
            def decoder(self):
                return func

    # Attach the new class to the module's global namespace and return it
    return attach_to_module(C, base_cls.__name__, func)


class BaseWrapped(object):
    def __call__(self, *args):
        return self


class Computation(BaseWrapped):
    _is_multi = False
    _is_state = False


class ComputationMulti(Computation):
    _is_multi = True


class StateComputation(Computation):
    _is_state = True


class StateComputationMulti(StateComputation):
    _is_multi = True


class KeyExtractor(BaseWrapped):
    pass


class OctetDecoder(BaseWrapped):
    pass


class OctetEncoder(BaseWrapped):
    pass


class ConnectorDecoder(BaseWrapped):
    pass


class ConnectorEncoder(BaseWrapped):
    pass


def computation(name):
    def wrapped(func):
        _validate_arity_compatability(func, 1)
        C = _wallaroo_wrap(name, func, Computation)
        return C()
    return wrapped


def state_computation(name, state):
    def wrapped(func):
        _validate_arity_compatability(func, 2)
        C = _wallaroo_wrap(name, func, StateComputation, state=state)
        # C = _wallaroo_wrap(name, func, StateComputation, state=StateBuilder(state))
        return C()
    return wrapped

# def state_computation(name):
#     def wrapped(func):
#         _validate_arity_compatability(func, 2)
#         C = _wallaroo_wrap(name, func, StateComputation)
#         return C()
#     return wrapped


def computation_multi(name):
    def wrapped(func):
        _validate_arity_compatability(func, 1)
        C = _wallaroo_wrap(name, func, ComputationMulti)
        return C()
    return wrapped

def state_computation_multi(name, state):
    def wrapped(func):
        _validate_arity_compatability(func, 2)
        C = _wallaroo_wrap(name, func, StateComputationMulti, state=StateBuilder(state))
        return C()
    return wrapped

# def state_computation_multi(name):
#     def wrapped(func):
#         _validate_arity_compatability(func, 2)
#         C = _wallaroo_wrap(name, func, StateComputationMulti)
#         return C()
#     return wrapped


class StateBuilder(object):
    def __init__(self, state_cls):
        self.state_cls = state_cls

    def initial_state(self):
        return self.state_cls()



def key_extractor(func):
    _validate_arity_compatability(func, 1)
    C = _wallaroo_wrap(func.__name__, func, KeyExtractor)
    return C()


def decoder(header_length, length_fmt):
    def wrapped(func):
        _validate_arity_compatability(func, 1)
        C = _wallaroo_wrap(func.__name__, func, OctetDecoder,
                           header_length = header_length,
                           length_fmt = length_fmt)
        return C()
    return wrapped


def encoder(func):
    _validate_arity_compatability(func, 1)
    C = _wallaroo_wrap(func.__name__, func, OctetEncoder)
    return C()


class TCPSourceConfig(object):
    def __init__(self, host, port, decoder):
        self._host = host
        self._port = port
        self._decoder = decoder

    def to_tuple(self):
        return ("tcp", self._host, self._port, self._decoder)


class GenSourceConfig(object):
    def __init__(self, gen_instance):
        self._gen = gen_instance

    def to_tuple(self):
        return ("gen", self._gen)


class TCPSinkConfig(object):
    def __init__(self, host, port, encoder):
        self._host = host
        self._port = port
        self._encoder = encoder

    def to_tuple(self):
        return ("tcp", self._host, self._port, self._encoder)


class CustomKafkaSourceCLIParser(object):
    def __init__(self, args, decoder):
        (in_topic, in_brokers,
        in_log_level) = kafka_parse_source_options(args)

        self.topic = in_topic
        self.brokers = in_brokers
        self.log_level = in_log_level
        self.decoder = decoder

    def to_tuple(self):
        return ("kafka", self.topic, self.brokers, self.log_level, self.decoder)


class CustomKafkaSinkCLIParser(object):
    def __init__(self, args, encoder):
        (out_topic, out_brokers, out_log_level, out_max_produce_buffer_ms,
         out_max_message_size) = kafka_parse_sink_options(args)

        self.topic = out_topic
        self.brokers = out_brokers
        self.log_level = out_log_level
        self.max_produce_buffer_ms = out_max_produce_buffer_ms
        self.max_message_size = out_max_message_size
        self.encoder = encoder

    def to_tuple(self):
        return ("kafka", self.topic, self.brokers, self.log_level,
                self.max_produce_buffer_ms, self.max_message_size, self.encoder)


class DefaultKafkaSourceCLIParser(object):
    def __init__(self, decoder, name="kafka_source"):
        self.decoder = decoder
        self.name = name

    def to_tuple(self):
        return ("kafka-internal", self.name, self.decoder)


class DefaultKafkaSinkCLIParser(object):
    def __init__(self, encoder, name="kafka_sink"):
        self.encoder = encoder
        self.name = name

    def to_tuple(self):
        return ("kafka-internal", self.name, self.encoder)


def tcp_parse_input_addrs(args):
    parser = argparse.ArgumentParser(prog="wallaroo")
    parser.add_argument('-i', '--in', dest="input_addrs")
    input_addrs = parser.parse_known_args(args)[0].input_addrs
    # split H1:P1,H2:P2... into [(H1, P1), (H2, P2), ...]
    return [tuple(x.split(':')) for x in input_addrs.split(',')]


def tcp_parse_output_addrs(args):
    parser = argparse.ArgumentParser(prog="wallaroo")
    parser.add_argument('-o', '--out', dest="output_addrs")
    output_addrs = parser.parse_known_args(args)[0].output_addrs
    # split H1:P1,H2:P2... into [(H1, P1), (H2, P2), ...]
    return [tuple(x.split(':')) for x in output_addrs.split(',')]


def kafka_parse_source_options(args):
    parser = argparse.ArgumentParser(prog="wallaroo")
    parser.add_argument('--kafka_source_topic', dest="topic",
                        default="")
    parser.add_argument('--kafka_source_brokers', dest="brokers",
                        default="")
    parser.add_argument('--kafka_source_log_level', dest="log_level",
                        default="Warn",
                        choices=["Fine", "Info", "Warn", "Error"])

    known_args = parser.parse_known_args(args)[0]

    brokers = [_kafka_parse_broker(b) for b in known_args.brokers.split(",")]

    return (known_args.topic, brokers, known_args.log_level)


def kafka_parse_sink_options(args):
    parser = argparse.ArgumentParser(prog="wallaroo")
    parser.add_argument('--kafka_sink_topic', dest="topic",
                        default="")
    parser.add_argument('--kafka_sink_brokers', dest="brokers",
                        default="")
    parser.add_argument('--kafka_sink_log_level', dest="log_level",
                        default="Warn",
                        choices=["Fine", "Info", "Warn", "Error"])
    parser.add_argument('--kafka_sink_max_produce_buffer_ms',
                        dest="max_produce_buffer_ms",
                        type=int,
                        default=0)
    parser.add_argument('--kafka_sink_max_message_size',
                        dest="max_message_size",
                        type=int,
                        default=100000)

    known_args = parser.parse_known_args(args)[0]

    brokers = [_kafka_parse_broker(b) for b in known_args.brokers.split(",")]

    return (known_args.topic, brokers, known_args.log_level,
            known_args.max_produce_buffer_ms, known_args.max_message_size)


def _kafka_parse_broker(broker):
    """
    `broker` is a string of `host[:port]`, return a tuple of `(host, port)`
    """
    host_and_port = broker.split(":")

    host = host_and_port[0]
    port = "9092"

    if len(host_and_port) == 2:
        port = host_and_port[1]

    return (host, port)


# Each node is a list of stages. Each of these lists will either begin with a "source" stage
# (if it is a leaf of the tree) or a "merge" stage (if it is not a leaf).
class _PipelineTree(object):
    def __init__(self, source_stage):
        self.root_idx = 0
        self.vs = [[source_stage]]
        self.es = [[]]

    def is_empty(self):
        return len(self.vs == 0)

    def add_stage(self, stage):
        self.vs[self.root_idx].append(stage)
        return self

    def merge(self, p_graph):
        idx = len(self.vs)
        self.vs.append([])
        self.es.append([self.root_idx])
        self.root_idx = idx
        diff = len(self.vs)
        for v in p_graph.vs:
            stages_clone = []
            for stage in v:
                stages_clone.append(stage)
            self.vs.append(stages_clone)
        for es in p_graph.es:
            new_es = []
            for e_idx in es:
                new_es.append(e_idx + diff)
            self.es.append(new_es)
        self.es[self.root_idx].append(p_graph.root_idx + diff)
        return self

    def to_tuple(self, app_name):
        p_tree = self.clone()
        return (app_name, p_tree.root_idx, p_tree.vs, p_tree.es)

    def clone(self):
        new_vs = []
        new_es = []
        for v in self.vs:
            new_stages = []
            for stage in v:
                new_stages.append(stage)
            new_vs.append(new_stages)
        for es in self.es:
            new_outs = []
            for out in es:
                new_outs.append(out)
            new_es.append(new_outs)
        pt = _PipelineTree(None)
        pt.root_idx = self.root_idx
        pt.vs = new_vs
        pt.es = new_es
        return pt
