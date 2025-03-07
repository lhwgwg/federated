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
#
# pytype: skip-file
# This modules disables the Pytype analyzer, see
# https://github.com/tensorflow/federated/blob/main/docs/pytype.md for more
# information.
"""Definitions of specific computation wrapper instances."""

from tensorflow_federated.python.core.impl.computation import computation_impl
from tensorflow_federated.python.core.impl.context_stack import context_stack_impl
from tensorflow_federated.python.core.impl.federated_context import federated_computation_utils
from tensorflow_federated.python.core.impl.tensorflow_context import tensorflow_serialization
from tensorflow_federated.python.core.impl.types import type_analysis
from tensorflow_federated.python.core.impl.wrappers import computation_wrapper


def _tf_wrapper_fn(parameter_type, name):
  """Wrapper function to plug Tensorflow logic into the TFF framework."""
  del name  # Unused.
  if not type_analysis.is_tensorflow_compatible_type(parameter_type):
    raise TypeError('`tf_computation`s can accept only parameter types with '
                    'constituents `SequenceType`, `StructType` '
                    'and `TensorType`; you have attempted to create one '
                    'with the type {}.'.format(parameter_type))
  ctx_stack = context_stack_impl.context_stack
  tf_serializer = tensorflow_serialization.tf_computation_serializer(
      parameter_type, ctx_stack)
  arg = next(tf_serializer)
  try:
    result = yield arg
  except Exception as e:  # pylint: disable=broad-except
    tf_serializer.throw(e)
  comp_pb, extra_type_spec = tf_serializer.send(result)
  tf_serializer.close()
  yield computation_impl.ConcreteComputation(comp_pb, ctx_stack,
                                             extra_type_spec)


tensorflow_wrapper = computation_wrapper.ComputationWrapper(
    computation_wrapper.PythonTracingStrategy(_tf_wrapper_fn))
tensorflow_wrapper.__doc__ = (
    """Decorates/wraps Python functions and defuns as TFF TensorFlow computations.

  This symbol can be used as either a decorator or a wrapper applied to a
  function given to it as an argument. The supported patterns and examples of
  usage are as follows:

  1. Convert an existing function inline into a TFF computation. This is the
     simplest mode of usage, and how one can embed existing non-TFF code for
     use with the TFF framework. In this mode, one invokes
     `tff.tf_computation` with a pair of arguments, the first being a
     function/defun that contains the logic, and the second being the TFF type
     of the parameter:

     ```python
     foo = tff.tf_computation(lambda x: x > 10, tf.int32)
     ```

     After executing the above code snippet, `foo` becomes an instance of the
     abstract base class `Computation`. Like all computations, it has the
     `type_signature` property:

     ```python
     str(foo.type_signature) == '(int32 -> bool)'
     ```

     The function passed as a parameter doesn't have to be a lambda, it can
     also be an existing Python function or a defun. Here's how to construct
     a computation from the standard TensorFlow operator `tf.add`:

     ```python
     foo = tff.tf_computation(tf.add, (tf.int32, tf.int32))
     ```

     The resulting type signature is as expected:

     ```python
     str(foo.type_signature) == '(<int32,int32> -> int32)'
     ```

     If one intends to create a computation that doesn't accept any arguments,
     the type argument is simply omitted. The function must be a no-argument
     function as well:

     ```python
     foo = tf_computation(lambda: tf.constant(10))
     ```

  2. Decorate a Python function or a TensorFlow defun with a TFF type to wrap
     it as a TFF computation. The only difference between this mode of usage
     and the one mentioned above is that instead of passing the function/defun
     as an argument, `tff.tf_computation` along with the optional type specifier
     is written above the function/defun's body.

     Here's an example of a computation that accepts a parameter:

     ```python
     @tff.tf_computation(tf.int32)
     def foo(x):
       return x > 10
     ```

     One can think of this mode of usage as merely a syntactic sugar for the
     example already given earlier:

     ```python
     foo = tff.tf_computation(lambda x: x > 10, tf.int32)
     ```

     Here's an example of a no-parameter computation:

     ```python
     @tff.tf_computation
     def foo():
       return tf.constant(10)
     ```

     Again, this is merely syntactic sugar for the example given earlier:

     ```python
     foo = tff.tf_computation(lambda: tf.constant(10))
     ```

     If the Python function has multiple decorators, `tff.tf_computation` should
     be the outermost one (the one that appears first in the sequence).

  3. Create a polymorphic callable to be instantiated based on arguments,
     similarly to TensorFlow defuns that have been defined without an input
     signature.

     This mode of usage is symmetric to those above. One simply omits the type
     specifier, and applies `tff.tf_computation` as a decorator or wrapper to a
     function/defun that does expect parameters.

     Here's an example of wrapping a lambda as a polymorphic callable:

     ```python
     foo = tff.tf_computation(lambda x, y: x > y)
     ```

     The resulting `foo` can be used in the same ways as if it were had the
     type been declared; the corresponding computation is simply created on
     demand, in the same way as how polymorphic TensorFlow defuns create and
     cache concrete function definitions for each combination of argument
     types.

     ```python
     ...foo(1, 2)...
     ...foo(0.5, 0.3)...
     ```

     Here's an example of creating a polymorphic callable via decorator:

     ```python
     @tff.tf_computation
     def foo(x, y):
       return x > y
     ```

     The syntax is symmetric to all examples already shown.

  Args:
    *args: Either a function/defun, or TFF type spec, or both (function first),
      or neither, as documented in the 3 patterns and examples of usage above.

  Returns:
    If invoked with a function as an argument, returns an instance of a TFF
    computation constructed based on this function. If called without one, as
    in the typical decorator style of usage, returns a callable that expects
    to be called with the function definition supplied as a parameter; see the
    patterns and examples of usage above.
  """)


def _federated_computation_wrapper_fn(parameter_type, name):
  """Wrapper function to plug orchestration logic into the TFF framework."""
  ctx_stack = context_stack_impl.context_stack
  if parameter_type is None:
    parameter_name = None
  else:
    parameter_name = 'arg'
  fn_generator = federated_computation_utils.federated_computation_serializer(
      parameter_name=parameter_name,
      parameter_type=parameter_type,
      context_stack=ctx_stack,
      suggested_name=name)
  arg = next(fn_generator)
  try:
    result = yield arg
  except Exception as e:  # pylint: disable=broad-except
    fn_generator.throw(e)
  target_lambda, extra_type_spec = fn_generator.send(result)
  fn_generator.close()
  yield computation_impl.ConcreteComputation(target_lambda.proto, ctx_stack,
                                             extra_type_spec)


federated_computation_wrapper = computation_wrapper.ComputationWrapper(
    computation_wrapper.PythonTracingStrategy(
        _federated_computation_wrapper_fn))
federated_computation_wrapper.__doc__ = (
    """Decorates/wraps Python functions as TFF federated/composite computations.

  The term *federated computation* as used here refers to any computation that
  uses TFF programming abstractions. Examples of such computations may include
  federated training or federated evaluation that involve both client-side and
  server-side logic and involve network communication. However, this
  decorator/wrapper can also be used to construct composite computations that
  only involve local processing on a client or on a server.

  The main feature that distinguishes *federated computation* function bodies
  in Python from the bodies of TensorFlow defuns is that whereas in the latter,
  one slices and dices `tf.Tensor` instances using a variety of TensorFlow ops,
  in the former one slices and dices `tff.Value` instances using TFF operators.

  The supported modes of usage are identical to those for `tff.tf_computation`.

  Example:

    ```python
    @tff.federated_computation((tff.FunctionType(tf.int32, tf.int32), tf.int32))
    def foo(f, x):
      return f(f(x))
    ```

    The above defines `foo` as a function that takes a tuple consisting of an
    unary integer operator as the first element, and an integer as the second
    element, and returns the result of applying the unary operator to the
    integer twice. The body of `foo` does not contain federated communication
    operators, but we define it with `tff.federated_computation` as it can be
    used as building block in any section of TFF code (except inside sections
    of pure TensorFlow logic).

  Args:
    *args: Either a Python function, or TFF type spec, or both (function first),
      or neither. See also `tff.tf_computation` for an extended documentation.

  Returns:
    If invoked with a function as an argument, returns an instance of a TFF
    computation constructed based on this function. If called without one, as
    in the typical decorator style of usage, returns a callable that expects
    to be called with the function definition supplied as a parameter. See
    also `tff.tf_computation` for an extended documentation.
  """)
