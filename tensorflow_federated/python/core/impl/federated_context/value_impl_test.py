# Copyright 2018, The TensorFlow Federated Authors.
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
import dataclasses
from typing import Any

from absl.testing import absltest
from absl.testing import parameterized
import attr
import numpy as np
import tensorflow as tf

from tensorflow_federated.python.common_libs import structure
from tensorflow_federated.python.core.api import computations
from tensorflow_federated.python.core.impl.compiler import building_blocks
from tensorflow_federated.python.core.impl.context_stack import context_stack_impl
from tensorflow_federated.python.core.impl.federated_context import federated_computation_context
from tensorflow_federated.python.core.impl.federated_context import value_impl
from tensorflow_federated.python.core.impl.types import computation_types
from tensorflow_federated.python.core.impl.types import placements


@dataclasses.dataclass
class TestDataclass:
  x: Any
  y: Any


@attr.s(auto_attribs=True)
class TestAttrClass:
  x: Any
  y: Any


class ValueTest(parameterized.TestCase):

  def run(self, result=None):
    fc_context = federated_computation_context.FederatedComputationContext(
        context_stack_impl.context_stack)
    with context_stack_impl.context_stack.install(fc_context):
      super(ValueTest, self).run(result)

  def bound_symbols(self):
    return context_stack_impl.context_stack.current.symbol_bindings

  def test_raises_on_boolean_ops(self):
    x_comp = building_blocks.Reference('foo', tf.bool)
    x = value_impl.Value(x_comp)
    with self.assertRaises(TypeError):
      assert x

  def test_value_impl_with_reference(self):
    x_comp = building_blocks.Reference('foo', tf.int32)
    x = value_impl.Value(x_comp)
    self.assertIs(x.comp, x_comp)
    self.assertEqual(str(x.type_signature), 'int32')
    self.assertEqual(repr(x), 'Reference(\'foo\', TensorType(tf.int32))')
    self.assertEqual(str(x), 'foo')
    with self.assertRaises(SyntaxError):
      x(10)

  def test_value_impl_with_selection(self):
    x = value_impl.Value(
        building_blocks.Reference('foo', [('bar', tf.int32), ('baz', tf.bool)]))
    self.assertContainsSubset(['bar', 'baz'], dir(x))
    self.assertLen(x, 2)
    y = x.bar
    self.assertIsInstance(y, value_impl.Value)
    self.assertEqual(str(y.type_signature), 'int32')
    self.assertEqual(str(y), 'foo.bar')
    z = x['baz']
    self.assertEqual(str(z.type_signature), 'bool')
    self.assertEqual(str(z), 'foo.baz')
    with self.assertRaises(AttributeError):
      _ = x.bak
    x0 = x[0]
    self.assertIsInstance(x0, value_impl.Value)
    self.assertEqual(str(x0.type_signature), 'int32')
    self.assertEqual(str(x0), 'foo[0]')
    x1 = x[1]
    self.assertEqual(str(x1.type_signature), 'bool')
    self.assertEqual(str(x1), 'foo[1]')
    with self.assertRaises(IndexError):
      _ = x[2]
    with self.assertRaises(IndexError):
      _ = x[-1]
    self.assertEqual(','.join(str(e) for e in iter(x)), 'foo[0],foo[1]')
    self.assertEqual(','.join(str(e.type_signature) for e in iter(x)),
                     'int32,bool')
    with self.assertRaises(SyntaxError):
      x(10)

  def test_value_impl_with_tuple(self):
    x_comp = building_blocks.Reference('foo', tf.int32)
    y_comp = building_blocks.Reference('bar', tf.bool)
    z = value_impl.Value(building_blocks.Struct([x_comp, ('y', y_comp)]))
    self.assertIsInstance(z, value_impl.Value)
    self.assertEqual(str(z.type_signature), '<int32,y=bool>')
    self.assertEqual(str(z), '<foo,y=bar>')
    self.assertContainsSubset(['y'], dir(z))
    self.assertEqual(str(z.y), 'bar')
    self.assertIs(z.y.comp, y_comp)
    self.assertLen(z, 2)
    self.assertEqual(str(z[0]), 'foo')
    self.assertIs(z[0].comp, x_comp)
    self.assertEqual(str(z['y']), 'bar')
    self.assertIs(z['y'].comp, y_comp)
    self.assertEqual(','.join(str(e) for e in iter(z)), 'foo,bar')
    with self.assertRaises(SyntaxError):
      z(10)

  def test_value_impl_with_call(self):
    x = value_impl.Value(
        building_blocks.Reference(
            'foo', computation_types.FunctionType(tf.int32, tf.bool)),)
    y = value_impl.Value(building_blocks.Reference('bar', tf.int32))
    z = x(y)
    self.assertIsInstance(z, value_impl.Value)
    self.assertEqual(str(z.type_signature), 'bool')
    self.assertEqual(str(z), 'fc_FEDERATED_symbol_0')
    bound_symbols = self.bound_symbols()
    self.assertLen(bound_symbols, 1)
    self.assertEqual(bound_symbols[0][0], str(z))
    self.assertEqual(str(bound_symbols[0][1]), 'foo(bar)')
    with self.assertRaises(TypeError):
      x()
    w = value_impl.Value(building_blocks.Reference('bak', tf.float32))
    with self.assertRaises(TypeError):
      x(w)

  def test_value_impl_with_lambda(self):
    arg_name = 'arg'
    arg_type = [('f', computation_types.FunctionType(tf.int32, tf.int32)),
                ('x', tf.int32)]
    result_value = (lambda arg: arg.f(arg.f(arg.x)))(
        value_impl.Value(building_blocks.Reference(arg_name, arg_type)))
    self.assertIsInstance(result_value, value_impl.Value)
    self.assertEqual(str(result_value.type_signature), 'int32')
    self.assertEqual(str(result_value), 'fc_FEDERATED_symbol_1')
    bound_symbols = self.bound_symbols()
    self.assertLen(bound_symbols, 2)
    self.assertEqual(bound_symbols[1][0], 'fc_FEDERATED_symbol_1')
    self.assertEqual(str(bound_symbols[1][1]), 'arg.f(fc_FEDERATED_symbol_0)')
    self.assertEqual(bound_symbols[0][0], 'fc_FEDERATED_symbol_0')
    self.assertEqual(str(bound_symbols[0][1]), 'arg.f(arg.x)')

  def test_value_impl_with_plus(self):
    x = value_impl.Value(building_blocks.Reference('x', tf.int32),)
    y = value_impl.Value(building_blocks.Reference('y', tf.int32))
    z = x + y
    self.assertIsInstance(z, value_impl.Value)
    self.assertEqual(str(z.type_signature), 'int32')
    self.assertEqual(str(z), 'fc_FEDERATED_symbol_0')
    bindings = self.bound_symbols()
    self.assertLen(bindings, 1)
    name, comp = bindings[0]
    self.assertEqual(name, 'fc_FEDERATED_symbol_0')
    self.assertEqual(comp.compact_representation(), 'generic_plus(<x,y>)')

  def test_to_value_for_tuple(self):
    x = value_impl.Value(building_blocks.Reference('foo', tf.int32),)
    y = value_impl.Value(building_blocks.Reference('bar', tf.bool),)
    v = value_impl.to_value((x, y), None)
    self.assertIsInstance(v, value_impl.Value)
    self.assertEqual(str(v), '<foo,bar>')

  def test_to_value_for_dataclass(self):
    x = value_impl.Value(building_blocks.Reference('foo', tf.int32))
    y = value_impl.Value(building_blocks.Reference('bar', tf.int32))
    v = value_impl.to_value(TestDataclass(x, y), None)
    self.assertIsInstance(v, value_impl.Value)
    self.assertEqual(str(v), '<x=foo,y=bar>')

  def test_to_value_for_attrs_class(self):
    x = value_impl.Value(building_blocks.Reference('foo', tf.int32))
    y = value_impl.Value(building_blocks.Reference('bar', tf.int32))
    v = value_impl.to_value(TestAttrClass(x, y), None)
    self.assertIsInstance(v, value_impl.Value)
    self.assertEqual(str(v), '<x=foo,y=bar>')

  def test_to_value_for_nested_dataclass(self):
    x = value_impl.Value(building_blocks.Reference('foo', tf.int32))
    y = value_impl.Value(building_blocks.Reference('bar', tf.int32))
    v = value_impl.to_value(
        TestDataclass(TestDataclass(x, y), TestDataclass(x, y)), None)
    self.assertIsInstance(v, value_impl.Value)
    self.assertEqual(str(v), '<x=<x=foo,y=bar>,y=<x=foo,y=bar>>')

  def test_to_value_for_nested_attrs_class(self):
    x = value_impl.Value(building_blocks.Reference('foo', tf.int32))
    y = value_impl.Value(building_blocks.Reference('bar', tf.int32))
    v = value_impl.to_value(
        TestAttrClass(TestAttrClass(x, y), TestAttrClass(x, y)), None)
    self.assertIsInstance(v, value_impl.Value)
    self.assertEqual(str(v), '<x=<x=foo,y=bar>,y=<x=foo,y=bar>>')

  def test_to_value_for_list(self):
    x = value_impl.Value(building_blocks.Reference('foo', tf.int32))
    y = value_impl.Value(building_blocks.Reference('bar', tf.bool))
    v = value_impl.to_value([x, y], None)
    self.assertIsInstance(v, value_impl.Value)
    self.assertEqual(str(v), '<foo,bar>')

  def test_to_value_for_dict_not_supported(self):
    x = value_impl.Value(building_blocks.Reference('foo', tf.int32))
    with self.assertRaises(TypeError):
      value_impl.to_value({'a': x}, None)

  def test_to_value_for_ordered_dict(self):
    x = value_impl.Value(building_blocks.Reference('foo', tf.int32))
    y = value_impl.Value(building_blocks.Reference('bar', tf.bool))
    v = value_impl.to_value(collections.OrderedDict([('b', y), ('a', x)]), None)
    self.assertIsInstance(v, value_impl.Value)
    self.assertEqual(str(v), '<b=bar,a=foo>')

  def test_to_value_for_named_tuple(self):
    x = value_impl.Value(building_blocks.Reference('foo', tf.int32))
    y = value_impl.Value(building_blocks.Reference('bar', tf.bool))
    v = value_impl.to_value(collections.namedtuple('_', 'a b')(x, y), None)
    self.assertIsInstance(v, value_impl.Value)
    self.assertEqual(str(v), '<a=foo,b=bar>')

  def test_to_value_for_structure(self):
    x = value_impl.Value(building_blocks.Reference('foo', tf.int32))
    y = value_impl.Value(building_blocks.Reference('bar', tf.bool))
    v = value_impl.to_value(structure.Struct([('a', x), ('b', y)]), None)
    self.assertIsInstance(v, value_impl.Value)
    self.assertEqual(str(v), '<a=foo,b=bar>')

  def test_to_value_for_placements(self):
    clients = value_impl.to_value(placements.CLIENTS, None)
    self.assertIsInstance(clients, value_impl.Value)
    self.assertEqual(str(clients.type_signature), 'placement')
    self.assertEqual(str(clients), 'CLIENTS')

  def test_to_value_for_computations(self):
    val = value_impl.to_value(
        computations.tf_computation(lambda: tf.constant(10)), None)
    self.assertIsInstance(val, value_impl.Value)
    self.assertEqual(str(val.type_signature), '( -> int32)')

  def test_to_value_with_string(self):
    value = value_impl.to_value('a', tf.string)
    self.assertIsInstance(value, value_impl.Value)
    self.assertEqual(str(value.type_signature), 'string')

  def test_to_value_with_int(self):
    value = value_impl.to_value(1, tf.int32)
    self.assertIsInstance(value, value_impl.Value)
    self.assertEqual(str(value.type_signature), 'int32')

  def test_to_value_with_float(self):
    value = value_impl.to_value(1.0, tf.float32)
    self.assertIsInstance(value, value_impl.Value)
    self.assertEqual(str(value.type_signature), 'float32')

  def test_to_value_with_bool(self):
    value = value_impl.to_value(True, tf.bool)
    self.assertIsInstance(value, value_impl.Value)
    self.assertEqual(str(value.type_signature), 'bool')

  def test_to_value_with_np_int32(self):
    value = value_impl.to_value(np.int32(1), tf.int32)
    self.assertIsInstance(value, value_impl.Value)
    self.assertEqual(str(value.type_signature), 'int32')

  def test_to_value_with_np_int64(self):
    value = value_impl.to_value(np.int64(1), tf.int64)
    self.assertIsInstance(value, value_impl.Value)
    self.assertEqual(str(value.type_signature), 'int64')

  def test_to_value_with_np_float32(self):
    value = value_impl.to_value(np.float32(1.0), tf.float32)
    self.assertIsInstance(value, value_impl.Value)
    self.assertEqual(str(value.type_signature), 'float32')

  def test_to_value_with_np_float64(self):
    value = value_impl.to_value(np.float64(1.0), tf.float64)
    self.assertIsInstance(value, value_impl.Value)
    self.assertEqual(str(value.type_signature), 'float64')

  def test_to_value_with_np_bool(self):
    value = value_impl.to_value(np.bool_(1.0), tf.bool)
    self.assertIsInstance(value, value_impl.Value)
    self.assertEqual(str(value.type_signature), 'bool')

  def test_to_value_with_np_ndarray(self):
    value = value_impl.to_value(
        np.ndarray(shape=(2, 0), dtype=np.int32), (tf.int32, [2, 0]))
    self.assertIsInstance(value, value_impl.Value)
    self.assertEqual(str(value.type_signature), 'int32[2,0]')

  def test_to_value_with_list_of_ints(self):
    value = value_impl.to_value([1, 2, 3],
                                computation_types.SequenceType(tf.int32))
    self.assertIsInstance(value, value_impl.Value)
    self.assertEqual(str(value.type_signature), 'int32*')

  def test_to_value_sequence_in_tuple_with_type(self):
    expected_type = computation_types.StructWithPythonType(
        [computation_types.SequenceType(tf.int32)], tuple)
    value = value_impl.to_value(([1, 2, 3],), expected_type)
    value.type_signature.check_identical_to(expected_type)

  def test_to_value_with_empty_list_of_ints(self):
    value = value_impl.to_value([], computation_types.SequenceType(tf.int32))
    self.assertIsInstance(value, value_impl.Value)
    self.assertEqual(str(value.type_signature), 'int32*')

  def test_to_value_raises_type_error(self):
    with self.assertRaises(TypeError):
      value_impl.to_value(10, tf.bool)

  def test_tf_mapping_raises_helpful_error(self):
    with self.assertRaisesRegex(
        TypeError, 'TensorFlow construct (.*) has been '
        'encountered in a federated context.'):
      _ = value_impl.to_value(tf.constant(10), None)
    with self.assertRaisesRegex(
        TypeError, 'TensorFlow construct (.*) has been '
        'encountered in a federated context.'):
      _ = value_impl.to_value(tf.Variable(np.array([10.0])), None)

  def test_slicing_support_namedtuple(self):
    x = value_impl.Value(building_blocks.Reference('foo', tf.int32))
    y = value_impl.Value(building_blocks.Reference('bar', tf.bool))
    v = value_impl.to_value(collections.namedtuple('_', 'a b')(x, y), None)
    sliced_v = v[:int(len(v) / 2)]
    self.assertIsInstance(sliced_v, value_impl.Value)
    sliced_v = v[:4:2]
    self.assertEqual(str(sliced_v), '<foo>')
    self.assertIsInstance(sliced_v, value_impl.Value)
    sliced_v = v[4::-1]
    self.assertEqual(str(sliced_v), '<bar,foo>')
    self.assertIsInstance(sliced_v, value_impl.Value)
    with self.assertRaisesRegex(IndexError, 'slice 0 elements'):
      _ = v[2:4]

  def test_slicing_fails_non_namedtuple(self):
    v = value_impl.to_value(np.ones([10, 10, 10], dtype=np.float32), None)
    with self.assertRaisesRegex(TypeError, 'only supported for structure'):
      _ = v[:1]

  def test_slicing_support_non_tuple_underlying_comp(self):
    test_computation_building_blocks = building_blocks.Reference(
        'test', [tf.int32] * 5)
    v = value_impl.Value(test_computation_building_blocks)
    sliced_v = v[:4:2]
    self.assertIsInstance(sliced_v, value_impl.Value)
    sliced_v = v[4:2:-1]
    self.assertIsInstance(sliced_v, value_impl.Value)
    with self.assertRaisesRegex(IndexError, 'slice 0 elements'):
      _ = v[2:4:-1]

  @parameterized.named_parameters(('list', list), ('tuple', tuple))
  def test_slicing_tuple_values_from_front(self, sequence_type):

    def _to_value(cbb):
      return value_impl.to_value(cbb, None)

    t = sequence_type(range(0, 50, 10))
    v = _to_value(t)

    self.assertEqual((str(v.type_signature)), '<int32,int32,int32,int32,int32>')
    self.assertEqual(str(v[:]), str(v))

    sliced = v[:2]
    self.assertEqual((str(sliced.type_signature)), '<int32,int32>')
    self.assertEqual(
        str(sliced), '<fc_FEDERATED_symbol_0,fc_FEDERATED_symbol_1>')

    expected_symbol_bindings = [
        ('fc_FEDERATED_symbol_0', [r'comp#[a-zA-Z0-9]*()']),
        ('fc_FEDERATED_symbol_1', [r'comp#[a-zA-Z0-9]*()']),
        ('fc_FEDERATED_symbol_2', [r'comp#[a-zA-Z0-9]*()']),
        ('fc_FEDERATED_symbol_3', [r'comp#[a-zA-Z0-9]*()']),
        ('fc_FEDERATED_symbol_4', [r'comp#[a-zA-Z0-9]*()']),
    ]

    bindings = self.bound_symbols()
    for (bound_name, comp), (expected_name,
                             expected_regex) in zip(bindings,
                                                    expected_symbol_bindings):
      self.assertEqual(bound_name, expected_name)
      self.assertRegexMatch(comp.compact_representation(), expected_regex)

  @parameterized.named_parameters(('list', list), ('tuple', tuple))
  def test_slicing_tuple_values_from_back(self, sequence_type):

    def _to_value(cbb):
      return value_impl.to_value(cbb, None)

    t = sequence_type(range(0, 50, 10))
    v = _to_value(t)

    self.assertEqual((str(v.type_signature)), '<int32,int32,int32,int32,int32>')
    self.assertEqual(str(v[:]), str(v))

    sliced = v[-3:]
    self.assertEqual((str(sliced.type_signature)), '<int32,int32,int32>')
    self.assertEqual(
        str(sliced),
        '<fc_FEDERATED_symbol_2,fc_FEDERATED_symbol_3,fc_FEDERATED_symbol_4>')

    expected_symbol_bindings = [
        ('fc_FEDERATED_symbol_0', [r'comp#[a-zA-Z0-9]*()']),
        ('fc_FEDERATED_symbol_1', [r'comp#[a-zA-Z0-9]*()']),
        ('fc_FEDERATED_symbol_2', [r'comp#[a-zA-Z0-9]*()']),
        ('fc_FEDERATED_symbol_3', [r'comp#[a-zA-Z0-9]*()']),
        ('fc_FEDERATED_symbol_4', [r'comp#[a-zA-Z0-9]*()']),
    ]

    bindings = self.bound_symbols()
    for (bound_name, comp), (expected_name,
                             expected_regex) in zip(bindings,
                                                    expected_symbol_bindings):
      self.assertEqual(bound_name, expected_name)
      self.assertRegexMatch(comp.compact_representation(), expected_regex)

  @parameterized.named_parameters(('list', list), ('tuple', tuple))
  def test_slicing_tuple_values_skipping_steps(self, sequence_type):

    def _to_value(val):
      return value_impl.to_value(val, None)

    t = sequence_type(range(0, 50, 10))
    v = _to_value(t)

    sliced = v[::2]
    self.assertEqual((str(sliced.type_signature)), '<int32,int32,int32>')
    self.assertEqual(
        str(sliced),
        '<fc_FEDERATED_symbol_0,fc_FEDERATED_symbol_2,fc_FEDERATED_symbol_4>')

    expected_symbol_bindings = [
        ('fc_FEDERATED_symbol_0', [r'comp#[a-zA-Z0-9]*()']),
        ('fc_FEDERATED_symbol_1', [r'comp#[a-zA-Z0-9]*()']),
        ('fc_FEDERATED_symbol_2', [r'comp#[a-zA-Z0-9]*()']),
        ('fc_FEDERATED_symbol_3', [r'comp#[a-zA-Z0-9]*()']),
        ('fc_FEDERATED_symbol_4', [r'comp#[a-zA-Z0-9]*()']),
    ]

    bindings = self.bound_symbols()
    for (bound_name, comp), (expected_name,
                             expected_regex) in zip(bindings,
                                                    expected_symbol_bindings):
      self.assertEqual(bound_name, expected_name)
      self.assertRegexMatch(comp.compact_representation(), expected_regex)

  def test_getitem_resolution_federated_value_clients(self):
    federated_value = value_impl.to_value(
        building_blocks.Reference(
            'test',
            computation_types.FederatedType([tf.int32, tf.bool],
                                            placements.CLIENTS, False)), None)
    self.assertEqual(
        str(federated_value.type_signature), '{<int32,bool>}@CLIENTS')
    federated_attribute = federated_value[0]
    self.assertEqual(str(federated_attribute.type_signature), '{int32}@CLIENTS')

  def test_getitem_federated_slice_constructs_comp_clients(self):
    federated_value = value_impl.to_value(
        building_blocks.Reference(
            'test',
            computation_types.FederatedType([tf.int32, tf.bool],
                                            placements.CLIENTS, False)), None)
    self.assertEqual(
        str(federated_value.type_signature), '{<int32,bool>}@CLIENTS')
    identity = federated_value[:]
    self.assertEqual(str(identity.type_signature), '{<int32,bool>}@CLIENTS')
    self.assertEqual(str(identity), 'federated_map(<(x -> <x[0],x[1]>),test>)')

  def test_getitem_resolution_federated_value_server(self):
    federated_value = value_impl.to_value(
        building_blocks.Reference(
            'test',
            computation_types.FederatedType([tf.int32, tf.bool],
                                            placements.SERVER, True)), None)
    self.assertEqual(str(federated_value.type_signature), '<int32,bool>@SERVER')
    federated_attribute = federated_value[0]
    self.assertEqual(str(federated_attribute.type_signature), 'int32@SERVER')

  def test_getitem_federated_slice_constructs_comp_server(self):
    federated_value = value_impl.to_value(
        building_blocks.Reference(
            'test',
            computation_types.FederatedType([tf.int32, tf.bool],
                                            placements.SERVER, True)), None)
    self.assertEqual(str(federated_value.type_signature), '<int32,bool>@SERVER')
    identity = federated_value[:]
    self.assertEqual(str(identity.type_signature), '<int32,bool>@SERVER')
    self.assertEqual(
        str(identity), 'federated_apply(<(x -> <x[0],x[1]>),test>)')

  def test_getitem_key_resolution(self):
    federated_value = value_impl.to_value(
        building_blocks.Reference(
            'test',
            computation_types.FederatedType([('a', tf.int32), ('b', tf.bool)],
                                            placements.SERVER, True)), None)
    self.assertEqual(
        str(federated_value.type_signature), '<a=int32,b=bool>@SERVER')
    federated_attribute = federated_value['a']
    self.assertEqual(str(federated_attribute.type_signature), 'int32@SERVER')
    with self.assertRaises(AttributeError):
      _ = federated_value['badkey']

  def test_getattr_resolution_federated_value_server(self):
    federated_value = value_impl.to_value(
        building_blocks.Reference(
            'test',
            computation_types.FederatedType([('a', tf.int32), ('b', tf.bool)],
                                            placements.SERVER, True)), None)
    self.assertEqual(
        str(federated_value.type_signature), '<a=int32,b=bool>@SERVER')
    federated_attribute = federated_value.a
    self.assertEqual(str(federated_attribute.type_signature), 'int32@SERVER')

  def test_getattr_resolution_federated_value_clients(self):
    federated_value = value_impl.to_value(
        building_blocks.Reference(
            'test',
            computation_types.FederatedType([('a', tf.int32), ('b', tf.bool)],
                                            placements.CLIENTS, False)), None)
    self.assertEqual(
        str(federated_value.type_signature), '{<a=int32,b=bool>}@CLIENTS')
    federated_attribute = federated_value.a
    self.assertEqual(str(federated_attribute.type_signature), '{int32}@CLIENTS')

  def test_getattr_raises_federated_value_unknown_attr(self):
    federated_value_clients = value_impl.to_value(
        building_blocks.Reference(
            'test',
            computation_types.FederatedType([('a', tf.int32), ('b', tf.bool)],
                                            placements.CLIENTS, True)), None)
    self.assertEqual(
        str(federated_value_clients.type_signature), '<a=int32,b=bool>@CLIENTS')
    with self.assertRaisesRegex(AttributeError,
                                r'There is no such attribute \'c\''):
      _ = federated_value_clients.c
    federated_value_server = value_impl.to_value(
        building_blocks.Reference(
            'test',
            computation_types.FederatedType([('a', tf.int32), ('b', tf.bool)],
                                            placements.SERVER, True)), None)
    self.assertEqual(
        str(federated_value_server.type_signature), '<a=int32,b=bool>@SERVER')
    with self.assertRaisesRegex(AttributeError,
                                r'There is no such attribute \'c\''):
      _ = federated_value_server.c

  def test_getattr_federated_value_with_none_default_missing_name(self):
    federated_value = value_impl.to_value(
        building_blocks.Reference(
            'test',
            computation_types.FederatedType([('a', tf.int32), ('b', tf.bool)],
                                            placements.SERVER, True)), None)
    self.assertEqual(
        str(federated_value.type_signature), '<a=int32,b=bool>@SERVER')
    missing_attr = getattr(federated_value, 'c', None)
    self.assertIsNone(missing_attr)

  def test_getattr_non_federated_value_with_none_default_missing_name(self):
    struct_value = value_impl.to_value(
        building_blocks.Reference(
            'test',
            computation_types.StructType([('a', tf.int32), ('b', tf.bool)])),
        None)
    self.assertEqual(str(struct_value.type_signature), '<a=int32,b=bool>')
    missing_attr = getattr(struct_value, 'c', None)
    self.assertIsNone(missing_attr)

  def test_value_impl_dir(self):
    x_comp = building_blocks.Reference('foo', tf.int32)
    x = value_impl.Value(x_comp)

    result = dir(x)
    self.assertIsInstance(result, list)
    self.assertNotEmpty(result)
    self.assertIn('type_signature', result)

  def test_value_impl_help(self):
    x_comp = building_blocks.Reference('foo', tf.int32)
    x = value_impl.Value(x_comp)
    help(x)


if __name__ == '__main__':
  absltest.main()
