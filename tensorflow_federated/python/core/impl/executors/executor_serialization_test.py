# Copyright 2019, The TensorFlow Federated Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections

from absl.testing import parameterized
import tensorflow as tf

from tensorflow_federated.proto.v0 import computation_pb2
from tensorflow_federated.proto.v0 import executor_pb2
from tensorflow_federated.python.common_libs import structure
from tensorflow_federated.python.core.api import computations
from tensorflow_federated.python.core.impl.executors import executor_serialization
from tensorflow_federated.python.core.impl.types import computation_types
from tensorflow_federated.python.core.impl.types import placements
from tensorflow_federated.python.core.impl.types import type_serialization
from tensorflow_federated.python.core.impl.types import type_test_utils


class ExecutorServiceUtilsTest(tf.test.TestCase, parameterized.TestCase):

  def test_serialize_deserialize_tensor_value(self):
    x = tf.constant(10.0)
    type_spec = computation_types.TensorType(tf.as_dtype(x.dtype), x.shape)
    value_proto, value_type = executor_serialization.serialize_value(
        x, type_spec)
    self.assertIsInstance(value_proto, executor_pb2.Value)
    type_test_utils.assert_types_identical(
        value_type, computation_types.TensorType(tf.float32))
    y, type_spec = executor_serialization.deserialize_value(value_proto)
    type_test_utils.assert_types_identical(
        type_spec, computation_types.TensorType(tf.float32))
    self.assertAllEqual(x, y)

  def test_serialize_deserialize_tensor_value_with_different_dtype(self):
    x = tf.constant(10.0)
    value_proto, value_type = executor_serialization.serialize_value(
        x, computation_types.TensorType(tf.int32))
    self.assertIsInstance(value_proto, executor_pb2.Value)
    type_test_utils.assert_types_identical(
        value_type, computation_types.TensorType(tf.int32))
    y, type_spec = executor_serialization.deserialize_value(value_proto)
    type_test_utils.assert_types_identical(
        type_spec, computation_types.TensorType(tf.int32))
    self.assertEqual(y, 10)

  def test_serialize_deserialize_tensor_value_with_nontrivial_shape(self):
    x = tf.constant([10, 20, 30])
    value_proto, value_type = executor_serialization.serialize_value(
        x, computation_types.TensorType(tf.int32, [3]))
    self.assertIsInstance(value_proto, executor_pb2.Value)
    type_test_utils.assert_types_identical(
        value_type, computation_types.TensorType(tf.int32, [3]))
    y, type_spec = executor_serialization.deserialize_value(value_proto)
    type_test_utils.assert_types_identical(
        type_spec, computation_types.TensorType(tf.int32, [3]))
    self.assertAllEqual(x, y)

  def test_serialize_sequence_bad_element_type(self):
    x = tf.data.Dataset.range(5).map(lambda x: x * 2)
    with self.assertRaisesRegex(
        TypeError, r'Cannot serialize dataset .* int64\* .* float32\*.*'):
      _ = executor_serialization.serialize_value(
          x, computation_types.SequenceType(tf.float32))

  def test_serialize_sequence_not_a_dataset(self):
    with self.assertRaisesRegex(
        TypeError, r'Cannot serialize Python type int as .* float32\*'):
      _ = executor_serialization.serialize_value(
          5, computation_types.SequenceType(tf.float32))

  @parameterized.named_parameters(('as_dataset', lambda x: x),
                                  ('as_list', list))
  def test_serialize_deserialize_sequence_of_scalars(self, ds_repr_fn):
    ds = tf.data.Dataset.range(5).map(lambda x: x * 2)
    ds_repr = ds_repr_fn(ds)
    value_proto, value_type = executor_serialization.serialize_value(
        ds_repr, computation_types.SequenceType(tf.int64))
    self.assertIsInstance(value_proto, executor_pb2.Value)
    type_test_utils.assert_types_identical(
        value_type, computation_types.SequenceType(tf.int64))
    y, type_spec = executor_serialization.deserialize_value(value_proto)
    type_test_utils.assert_types_identical(
        type_spec, computation_types.SequenceType(tf.int64))
    self.assertAllEqual(list(y), [x * 2 for x in range(5)])

  @parameterized.named_parameters(('as_dataset', lambda x: x),
                                  ('as_list', list))
  def test_serialize_deserialize_sequence_of_tuples(self, ds_repr_fn):
    ds = tf.data.Dataset.range(5).map(
        lambda x: (x * 2, tf.cast(x, tf.int32), tf.cast(x - 1, tf.float32)))
    ds_repr = ds_repr_fn(ds)
    value_proto, value_type = executor_serialization.serialize_value(
        ds_repr,
        computation_types.SequenceType(
            element=(tf.int64, tf.int32, tf.float32)))
    expected_type = computation_types.SequenceType(
        (tf.int64, tf.int32, tf.float32))
    self.assertIsInstance(value_proto, executor_pb2.Value)
    type_test_utils.assert_types_identical(value_type, expected_type)
    y, type_spec = executor_serialization.deserialize_value(value_proto)
    # Only checking for equivalence, we don't have the Python container
    # after deserialization.
    type_test_utils.assert_types_equivalent(type_spec, expected_type)
    self.assertAllEqual(list(y), [(x * 2, x, x - 1.) for x in range(5)])

  @parameterized.named_parameters(('as_dataset', lambda x: x),
                                  ('as_list', list))
  def test_serialize_deserialize_sequence_of_namedtuples(self, ds_repr_fn):
    test_tuple_type = collections.namedtuple('TestTuple', ['a', 'b', 'c'])

    def make_test_tuple(x):
      return test_tuple_type(
          a=x * 2, b=tf.cast(x, tf.int32), c=tf.cast(x - 1, tf.float32))

    ds = tf.data.Dataset.range(5).map(make_test_tuple)
    ds_repr = ds_repr_fn(ds)
    element_type = computation_types.to_type(
        test_tuple_type(tf.int64, tf.int32, tf.float32))
    sequence_type = computation_types.SequenceType(element=element_type)
    value_proto, value_type = executor_serialization.serialize_value(
        ds_repr, sequence_type)
    self.assertIsInstance(value_proto, executor_pb2.Value)
    self.assertEqual(value_type, sequence_type)
    y, type_spec = executor_serialization.deserialize_value(value_proto)
    type_test_utils.assert_types_equivalent(type_spec, sequence_type)
    actual_values = list(y)
    expected_values = [
        test_tuple_type(a=x * 2, b=x, c=x - 1.) for x in range(5)
    ]
    for actual, expected in zip(actual_values, expected_values):
      self.assertAllClose(actual, expected)

  @parameterized.named_parameters(('as_dataset', lambda x: x),
                                  ('as_list', list))
  def test_serialize_deserialize_sequence_of_nested_structures(
      self, ds_repr_fn):
    test_tuple_type = collections.namedtuple('TestTuple', ['u', 'v'])

    def _make_nested_tf_structure(x):
      return collections.OrderedDict(
          b=tf.cast(x, tf.int32),
          a=tuple([
              x,
              test_tuple_type(x * 2, x * 3),
              collections.OrderedDict(x=x**2, y=x**3)
          ]))

    ds = tf.data.Dataset.range(5).map(_make_nested_tf_structure)
    ds_repr = ds_repr_fn(ds)
    element_type = computation_types.to_type(
        collections.OrderedDict(
            b=tf.int32,
            a=tuple([
                tf.int64,
                test_tuple_type(tf.int64, tf.int64),
                collections.OrderedDict(x=tf.int64, y=tf.int64),
            ])))
    sequence_type = computation_types.SequenceType(element=element_type)
    value_proto, value_type = executor_serialization.serialize_value(
        ds_repr, sequence_type)
    self.assertIsInstance(value_proto, executor_pb2.Value)
    type_test_utils.assert_types_identical(value_type, sequence_type)
    y, type_spec = executor_serialization.deserialize_value(value_proto)
    # These aren't the same because ser/de destroys the PyContainer
    type_test_utils.assert_types_equivalent(type_spec, sequence_type)

    def _build_expected_structure(x):
      return collections.OrderedDict(
          b=x,
          a=tuple([
              x,
              test_tuple_type(x * 2, x * 3),
              collections.OrderedDict(x=x**2, y=x**3)
          ]))

    actual_values = list(y)
    expected_values = [_build_expected_structure(x) for x in range(5)]
    for actual, expected in zip(actual_values, expected_values):
      self.assertEqual(type(actual), type(expected))
      self.assertAllClose(actual, expected)

  def test_serialize_deserialize_tensor_value_with_bad_shape(self):
    x = tf.constant([10, 20, 30])
    with self.assertRaises(TypeError):
      executor_serialization.serialize_value(x, tf.int32)

  def test_serialize_deserialize_computation_value(self):

    @computations.tf_computation
    def comp():
      return tf.constant(10)

    value_proto, value_type = executor_serialization.serialize_value(comp)
    self.assertEqual(value_proto.WhichOneof('value'), 'computation')
    type_test_utils.assert_types_identical(
        value_type,
        computation_types.FunctionType(parameter=None, result=tf.int32))
    comp, type_spec = executor_serialization.deserialize_value(value_proto)
    self.assertIsInstance(comp, computation_pb2.Computation)
    type_test_utils.assert_types_identical(
        type_spec,
        computation_types.FunctionType(parameter=None, result=tf.int32))

  def test_serialize_deserialize_nested_tuple_value_with_names(self):
    x = collections.OrderedDict(
        a=10, b=[20, 30], c=collections.OrderedDict(d=40))
    x_type = computation_types.to_type(
        collections.OrderedDict(
            a=tf.int32,
            b=[tf.int32, tf.int32],
            c=collections.OrderedDict(d=tf.int32)))
    value_proto, value_type = executor_serialization.serialize_value(x, x_type)
    self.assertIsInstance(value_proto, executor_pb2.Value)
    type_test_utils.assert_types_identical(value_type, x_type)
    y, type_spec = executor_serialization.deserialize_value(value_proto)
    # Don't assert on the Python container since it is lost in serialization.
    type_test_utils.assert_types_equivalent(type_spec, x_type)
    self.assertEqual(y, structure.from_container(x, recursive=True))

  def test_serialize_deserialize_nested_tuple_value_without_names(self):
    x = (10, 20)
    x_type = computation_types.to_type((tf.int32, tf.int32))
    value_proto, value_type = executor_serialization.serialize_value(x, x_type)
    self.assertIsInstance(value_proto, executor_pb2.Value)
    type_test_utils.assert_types_identical(value_type, x_type)
    y, type_spec = executor_serialization.deserialize_value(value_proto)
    type_test_utils.assert_types_equivalent(type_spec, x_type)
    self.assertEqual(y, structure.from_container((10, 20)))

  def test_serialize_deserialize_federated_at_clients(self):
    x = [10, 20]
    x_type = computation_types.at_clients(tf.int32)
    value_proto, value_type = executor_serialization.serialize_value(x, x_type)
    self.assertIsInstance(value_proto, executor_pb2.Value)
    type_test_utils.assert_types_identical(
        value_type, computation_types.at_clients(tf.int32))
    y, type_spec = executor_serialization.deserialize_value(value_proto)
    type_test_utils.assert_types_identical(
        type_spec, computation_types.at_clients(tf.int32))
    self.assertEqual(y, [10, 20])

  def test_deserialize_federated_value_with_unset_member_type(self):
    x = 10
    x_type = computation_types.to_type(tf.int32)
    member_proto, _ = executor_serialization.serialize_value(x, x_type)
    fully_specified_type_at_clients = type_serialization.serialize_type(
        computation_types.at_clients(tf.int32))

    unspecified_member_federated_type = computation_pb2.FederatedType(
        placement=fully_specified_type_at_clients.federated.placement,
        all_equal=fully_specified_type_at_clients.federated.all_equal)

    federated_proto = executor_pb2.Value.Federated(
        type=unspecified_member_federated_type, value=[member_proto])
    federated_value_proto = executor_pb2.Value(federated=federated_proto)

    self.assertIsInstance(member_proto, executor_pb2.Value)
    self.assertIsInstance(federated_value_proto, executor_pb2.Value)

    deserialized_federated_value, deserialized_type_spec = executor_serialization.deserialize_value(
        federated_value_proto)
    type_test_utils.assert_types_identical(
        deserialized_type_spec, computation_types.at_clients(tf.int32))
    self.assertEqual(deserialized_federated_value, [10])

  def test_deserialize_federated_value_with_incompatible_member_types_raises(
      self):
    x = 10
    x_type = computation_types.to_type(tf.int32)
    int_member_proto, _ = executor_serialization.serialize_value(x, x_type)
    y = 10.
    y_type = computation_types.to_type(tf.float32)
    float_member_proto, _ = executor_serialization.serialize_value(y, y_type)
    fully_specified_type_at_clients = type_serialization.serialize_type(
        computation_types.at_clients(tf.int32))

    unspecified_member_federated_type = computation_pb2.FederatedType(
        placement=fully_specified_type_at_clients.federated.placement,
        all_equal=False)

    federated_proto = executor_pb2.Value.Federated(
        type=unspecified_member_federated_type,
        value=[int_member_proto, float_member_proto])
    federated_value_proto = executor_pb2.Value(federated=federated_proto)

    self.assertIsInstance(int_member_proto, executor_pb2.Value)
    self.assertIsInstance(float_member_proto, executor_pb2.Value)
    self.assertIsInstance(federated_value_proto, executor_pb2.Value)

    with self.assertRaises(TypeError):
      executor_serialization.deserialize_value(federated_value_proto)

  def test_deserialize_federated_value_promotes_types(self):
    x = [10]
    smaller_type = computation_types.StructType([
        (None, computation_types.to_type(tf.int32))
    ])
    smaller_type_member_proto, _ = executor_serialization.serialize_value(
        x, smaller_type)
    larger_type = computation_types.StructType([
        ('a', computation_types.to_type(tf.int32))
    ])
    larger_type_member_proto, _ = executor_serialization.serialize_value(
        x, larger_type)
    type_at_clients = type_serialization.serialize_type(
        computation_types.at_clients(tf.int32))

    unspecified_member_federated_type = computation_pb2.FederatedType(
        placement=type_at_clients.federated.placement, all_equal=False)

    federated_proto = executor_pb2.Value.Federated(
        type=unspecified_member_federated_type,
        value=[larger_type_member_proto, smaller_type_member_proto])
    federated_value_proto = executor_pb2.Value(federated=federated_proto)

    self.assertIsInstance(smaller_type_member_proto, executor_pb2.Value)
    self.assertIsInstance(larger_type_member_proto, executor_pb2.Value)
    self.assertIsInstance(federated_value_proto, executor_pb2.Value)

    _, deserialized_type_spec = executor_serialization.deserialize_value(
        federated_value_proto)
    type_test_utils.assert_types_identical(
        deserialized_type_spec, computation_types.at_clients(larger_type))

  def test_serialize_deserialize_federated_at_server(self):
    x = 10
    x_type = computation_types.at_server(tf.int32)
    value_proto, value_type = executor_serialization.serialize_value(x, x_type)
    self.assertIsInstance(value_proto, executor_pb2.Value)
    type_test_utils.assert_types_identical(
        value_type, computation_types.at_server(tf.int32))
    y, type_spec = executor_serialization.deserialize_value(value_proto)
    type_test_utils.assert_types_identical(type_spec, x_type)
    self.assertEqual(y, 10)


class DatasetSerializationTest(tf.test.TestCase):

  def test_serialize_sequence_not_a_dataset(self):
    with self.assertRaisesRegex(TypeError, r'Expected .*Dataset.* found int'):
      _ = executor_serialization._serialize_dataset(5)

  def test_serialize_sequence_bytes_too_large(self):
    with self.assertRaisesRegex(ValueError,
                                r'Serialized size .* exceeds maximum allowed'):
      _ = executor_serialization._serialize_dataset(
          tf.data.Dataset.range(5), max_serialized_size_bytes=0)

  def test_roundtrip_sequence_of_scalars(self):
    x = tf.data.Dataset.range(5).map(lambda x: x * 2)
    serialized_bytes = executor_serialization._serialize_dataset(x)
    y = executor_serialization._deserialize_dataset_from_graph_def(
        serialized_bytes,
        element_type=computation_types.to_type(x.element_spec))
    self.assertEqual(x.element_spec, y.element_spec)
    self.assertAllEqual(list(y), [x * 2 for x in range(5)])

  def test_roundtrip_sequence_of_tuples(self):
    x = tf.data.Dataset.range(5).map(
        lambda x: (x * 2, tf.cast(x, tf.int32), tf.cast(x - 1, tf.float32)))
    serialized_bytes = executor_serialization._serialize_dataset(x)
    y = executor_serialization._deserialize_dataset_from_graph_def(
        serialized_bytes,
        element_type=computation_types.to_type(x.element_spec))
    self.assertEqual(x.element_spec, y.element_spec)
    self.assertAllEqual(list(y), [(x * 2, x, x - 1.) for x in range(5)])

  def test_roundtrip_sequence_of_singleton_tuples(self):
    x = tf.data.Dataset.range(5).map(lambda x: (x,))
    serialized_bytes = executor_serialization._serialize_dataset(x)
    y = executor_serialization._deserialize_dataset_from_graph_def(
        serialized_bytes,
        element_type=computation_types.to_type(x.element_spec))
    self.assertEqual(x.element_spec, y.element_spec)
    expected_values = [(x,) for x in range(5)]
    actual_values = list(y)
    self.assertAllEqual(expected_values, actual_values)

  def test_roundtrip_sequence_of_namedtuples(self):
    test_tuple_type = collections.namedtuple('TestTuple', ['a', 'b', 'c'])

    def make_test_tuple(x):
      return test_tuple_type(
          a=x * 2, b=tf.cast(x, tf.int32), c=tf.cast(x - 1, tf.float32))

    x = tf.data.Dataset.range(5).map(make_test_tuple)
    serialized_bytes = executor_serialization._serialize_dataset(x)
    y = executor_serialization._deserialize_dataset_from_graph_def(
        serialized_bytes,
        element_type=computation_types.to_type(x.element_spec))
    self.assertEqual(x.element_spec, y.element_spec)
    self.assertAllEqual(
        list(y), [test_tuple_type(a=x * 2, b=x, c=x - 1.) for x in range(5)])

  def test_roundtrip_sequence_of_nested_structures(self):
    test_tuple_type = collections.namedtuple('TestTuple', ['u', 'v'])

    def _make_nested_tf_structure(x):
      return collections.OrderedDict(
          b=tf.cast(x, tf.int32),
          a=(
              x,
              test_tuple_type(x * 2, x * 3),
              collections.OrderedDict(x=x**2, y=x**3),
          ))

    x = tf.data.Dataset.range(5).map(_make_nested_tf_structure)
    serialzied_bytes = executor_serialization._serialize_dataset(x)
    y = executor_serialization._deserialize_dataset_from_graph_def(
        serialzied_bytes,
        element_type=computation_types.to_type(x.element_spec))
    # Note: TF loses the `OrderedDict` during serialization, so the expectation
    # here is for a `dict` in the result.
    expected_element_spec = collections.OrderedDict(
        b=tf.TensorSpec([], tf.int32),
        a=(tf.TensorSpec([], tf.int64),
           test_tuple_type(
               tf.TensorSpec([], tf.int64), tf.TensorSpec([], tf.int64)),
           collections.OrderedDict(
               x=tf.TensorSpec([], tf.int64), y=tf.TensorSpec([], tf.int64))))
    self.assertEqual(y.element_spec, expected_element_spec)

    def _build_expected_structure(x):
      return collections.OrderedDict(
          b=x,
          a=(
              x,
              test_tuple_type(x * 2, x * 3),
              collections.OrderedDict(x=x**2, y=x**3),
          ))

    expected_values = (_build_expected_structure(x) for x in range(5))
    for actual, expected in zip(y, expected_values):
      self.assertAllClose(actual, expected)


class SerializeCardinalitiesTest(tf.test.TestCase):

  def test_serialize_deserialize_clients_and_server_cardinalities_roundtrip(
      self):
    client_and_server_cardinalities = {
        placements.CLIENTS: 10,
        placements.SERVER: 1
    }
    cardinalities_list = executor_serialization.serialize_cardinalities(
        client_and_server_cardinalities)
    for cardinality in cardinalities_list:
      self.assertIsInstance(cardinality, executor_pb2.Cardinality)
    reconstructed_cardinalities = executor_serialization.deserialize_cardinalities(
        cardinalities_list)
    self.assertEqual(client_and_server_cardinalities,
                     reconstructed_cardinalities)

  def test_serialize_deserialize_clients_alone(self):
    client_cardinalities = {placements.CLIENTS: 10}
    cardinalities_list = executor_serialization.serialize_cardinalities(
        client_cardinalities)
    for cardinality in cardinalities_list:
      self.assertIsInstance(cardinality, executor_pb2.Cardinality)
    reconstructed_cardinalities = executor_serialization.deserialize_cardinalities(
        cardinalities_list)
    self.assertEqual(client_cardinalities, reconstructed_cardinalities)


if __name__ == '__main__':
  tf.test.main()
