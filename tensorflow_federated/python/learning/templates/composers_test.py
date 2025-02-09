# Copyright 2021, The TensorFlow Federated Authors.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import collections

from absl.testing import parameterized
import tensorflow as tf

from tensorflow_federated.python.aggregators import mean
from tensorflow_federated.python.aggregators import sum_factory
from tensorflow_federated.python.common_libs import structure
from tensorflow_federated.python.core.api import computations
from tensorflow_federated.python.core.backends.native import execution_contexts
from tensorflow_federated.python.core.impl.federated_context import intrinsics
from tensorflow_federated.python.core.impl.types import computation_types
from tensorflow_federated.python.core.impl.types import placements
from tensorflow_federated.python.core.templates import measured_process
from tensorflow_federated.python.learning import keras_utils
from tensorflow_federated.python.learning import model_examples
from tensorflow_federated.python.learning import model_utils
from tensorflow_federated.python.learning.optimizers import sgdm
from tensorflow_federated.python.learning.templates import client_works
from tensorflow_federated.python.learning.templates import composers
from tensorflow_federated.python.learning.templates import distributors
from tensorflow_federated.python.learning.templates import finalizers
from tensorflow_federated.python.learning.templates import learning_process

FLOAT_TYPE = computation_types.TensorType(tf.float32)
MODEL_WEIGHTS_TYPE = computation_types.to_type(
    model_utils.ModelWeights(FLOAT_TYPE, ()))
CLIENTS_SEQUENCE_FLOAT_TYPE = computation_types.at_clients(
    computation_types.SequenceType(FLOAT_TYPE))


def empty_at_server():
  return intrinsics.federated_value((), placements.SERVER)


@computations.federated_computation()
def empty_init_fn():
  return empty_at_server()


@computations.tf_computation()
def test_init_model_weights_fn():
  return model_utils.ModelWeights(trainable=tf.constant(1.0), non_trainable=())


def test_distributor():

  @computations.federated_computation(
      empty_init_fn.type_signature.result,
      computation_types.at_server(MODEL_WEIGHTS_TYPE))
  def next_fn(state, value):
    return measured_process.MeasuredProcessOutput(
        state, intrinsics.federated_broadcast(value), empty_at_server())

  return distributors.DistributionProcess(empty_init_fn, next_fn)


def test_client_work():

  @computations.tf_computation()
  def make_result(value, data):
    return client_works.ClientResult(
        update=value.trainable,
        update_weight=data.reduce(0.0, lambda x, y: x + y))

  @computations.federated_computation(
      empty_init_fn.type_signature.result,
      computation_types.at_clients(MODEL_WEIGHTS_TYPE),
      CLIENTS_SEQUENCE_FLOAT_TYPE)
  def next_fn(state, value, client_data):
    result = intrinsics.federated_map(make_result, (value, client_data))
    return measured_process.MeasuredProcessOutput(state, result,
                                                  empty_at_server())

  return client_works.ClientWorkProcess(empty_init_fn, next_fn)


def test_aggregator():
  return mean.MeanFactory().create(FLOAT_TYPE, FLOAT_TYPE)


def test_finalizer():

  @computations.federated_computation(
      empty_init_fn.type_signature.result,
      computation_types.at_server(MODEL_WEIGHTS_TYPE),
      computation_types.at_server(FLOAT_TYPE))
  def next_fn(state, weights, updates):
    new_weights = intrinsics.federated_map(
        computations.tf_computation(lambda x, y: x + y),
        (weights.trainable, updates))
    new_weights = intrinsics.federated_zip(
        model_utils.ModelWeights(new_weights, ()))
    return measured_process.MeasuredProcessOutput(state, new_weights,
                                                  empty_at_server())

  return finalizers.FinalizerProcess(empty_init_fn, next_fn)


class ComposeLearningProcessTest(tf.test.TestCase):

  def test_learning_process_composes(self):
    process = composers.compose_learning_process(test_init_model_weights_fn,
                                                 test_distributor(),
                                                 test_client_work(),
                                                 test_aggregator(),
                                                 test_finalizer())

    self.assertIsInstance(process, learning_process.LearningProcess)
    self.assertEqual(
        process.initialize.type_signature.result.member.python_container,
        composers.LearningAlgorithmState)
    self.assertEqual(
        process.initialize.type_signature.result.member.global_model_weights,
        MODEL_WEIGHTS_TYPE)

    # Reported metrics have the expected fields.
    metrics_type = process.next.type_signature.result.metrics.member
    self.assertTrue(structure.has_field(metrics_type, 'distributor'))
    self.assertTrue(structure.has_field(metrics_type, 'client_work'))
    self.assertTrue(structure.has_field(metrics_type, 'aggregator'))
    self.assertTrue(structure.has_field(metrics_type, 'finalizer'))
    self.assertLen(metrics_type, 4)

  def test_one_arg_computation_init_raises(self):

    @computations.tf_computation(computation_types.TensorType(tf.float32))
    def init_model_weights_fn(x):
      return model_utils.ModelWeights(trainable=x, non_trainable=())

    with self.assertRaisesRegex(TypeError, 'Computation'):
      composers.compose_learning_process(init_model_weights_fn,
                                         test_distributor(), test_client_work(),
                                         test_aggregator(), test_finalizer())

  def test_not_tff_computation_init_raises(self):

    def init_model_weights_fn():
      return model_utils.ModelWeights(
          trainable=tf.constant(1.0), non_trainable=())

    with self.assertRaisesRegex(TypeError, 'Computation'):
      composers.compose_learning_process(init_model_weights_fn,
                                         test_distributor(), test_client_work(),
                                         test_aggregator(), test_finalizer())

  def test_federated_init_raises(self):

    @computations.federated_computation()
    def init_model_weights_fn():
      return intrinsics.federated_eval(test_init_model_weights_fn,
                                       placements.SERVER)

    with self.assertRaisesRegex(TypeError, 'unplaced'):
      composers.compose_learning_process(init_model_weights_fn,
                                         test_distributor(), test_client_work(),
                                         test_aggregator(), test_finalizer())

  def test_not_distributor_type_raises(self):
    distributor = test_distributor()
    bad_distributor = measured_process.MeasuredProcess(distributor.initialize,
                                                       distributor.next)
    with self.assertRaisesRegex(TypeError, 'DistributionProcess'):
      composers.compose_learning_process(test_init_model_weights_fn,
                                         bad_distributor, test_client_work(),
                                         test_aggregator(), test_finalizer())

  def test_not_client_work_type_raises(self):
    client_work = test_client_work()
    bad_client_work = measured_process.MeasuredProcess(client_work.initialize,
                                                       client_work.next)
    with self.assertRaisesRegex(TypeError, 'ClientWorkProcess'):
      composers.compose_learning_process(test_init_model_weights_fn,
                                         test_distributor(), bad_client_work,
                                         test_aggregator(), test_finalizer())

  def test_not_aggregator_type_raises(self):
    aggregator = test_aggregator()
    bad_aggregator = measured_process.MeasuredProcess(aggregator.initialize,
                                                      aggregator.next)
    with self.assertRaisesRegex(TypeError, 'AggregationProcess'):
      composers.compose_learning_process(test_init_model_weights_fn,
                                         test_distributor(), test_client_work(),
                                         bad_aggregator, test_finalizer())

  def test_unweighted_aggregator_raises(self):
    bad_aggregator = sum_factory.SumFactory().create(FLOAT_TYPE)
    with self.assertRaisesRegex(TypeError, 'weighted'):
      composers.compose_learning_process(test_init_model_weights_fn,
                                         test_distributor(), test_client_work(),
                                         bad_aggregator, test_finalizer())

  def test_not_finalizer_type_raises(self):
    finalizer = test_finalizer()
    bad_finalizer = measured_process.MeasuredProcess(finalizer.initialize,
                                                     finalizer.next)
    with self.assertRaisesRegex(TypeError, 'FinalizerProcess'):
      composers.compose_learning_process(test_init_model_weights_fn,
                                         test_distributor(), test_client_work(),
                                         test_aggregator(), bad_finalizer)

  # TODO(b/190334722): Add more tests that assert early errors are raised in the
  # _validate_args method, when adding custom error messages.


class VanillaFedAvgTest(tf.test.TestCase, parameterized.TestCase):

  def _test_data(self):
    return tf.data.Dataset.from_tensor_slices(
        collections.OrderedDict(
            x=[[1.0, 2.0], [3.0, 4.0]],
            y=[[5.0], [6.0]],
        )).batch(2)

  def _test_batch_loss(self, model, weights):
    tf.nest.map_structure(lambda w, v: w.assign(v),
                          model_utils.ModelWeights.from_model(model), weights)
    for batch in self._test_data().take(1):
      batch_output = model.forward_pass(batch, training=False)
    return batch_output.loss

  def test_loss_decreases(self):
    model_fn = model_examples.LinearRegression
    test_model = model_fn()
    fedavg = composers.build_basic_fedavg_process(
        model_fn=model_fn, client_learning_rate=0.1)
    client_data = [self._test_data()] * 3  # 3 clients with identical data.
    state = fedavg.initialize()
    last_loss = self._test_batch_loss(test_model, state.global_model_weights)
    for _ in range(5):
      fedavg_result = fedavg.next(state, client_data)
      state = fedavg_result.state
      metrics = fedavg_result.metrics
      loss = self._test_batch_loss(test_model, state.global_model_weights)
      self.assertLess(loss, last_loss)
      last_loss = loss
    self.assertIsInstance(state, composers.LearningAlgorithmState)
    self.assertLen(metrics, 4)
    for key in ['distributor', 'client_work', 'aggregator', 'finalizer']:
      self.assertIn(key, metrics)

  def test_get_set_model_weights_roundtrip(self):
    model_fn = model_examples.LinearRegression
    fedavg = composers.build_basic_fedavg_process(
        model_fn=model_fn, client_learning_rate=0.1)
    state = fedavg.initialize()
    model_weights = fedavg.get_model_weights(state)
    new_state = fedavg.set_model_weights(state, model_weights)
    self.assertAllClose(tf.nest.flatten(state), tf.nest.flatten(new_state))

  def test_get_set_model_weights_keras_model(self):

    def model_fn():
      keras_model = model_examples.build_linear_regression_keras_functional_model(
      )
      return keras_utils.from_keras_model(
          keras_model,
          loss=tf.keras.losses.MeanSquaredError(),
          input_spec=collections.OrderedDict(
              x=tf.TensorSpec(shape=[None, 2]),
              y=tf.TensorSpec(shape=[None, 1])))

    fedavg = composers.build_basic_fedavg_process(
        model_fn=model_fn, client_learning_rate=0.1)
    state = fedavg.initialize()
    # Create a local model and perform some pretraining.
    keras_model = model_examples.build_linear_regression_keras_functional_model(
    )
    keras_model.compile(optimizer='adam', loss='mse')
    keras_model.fit(self._test_data().map(lambda d: (d['x'], d['y'])))
    pretrained_weights = model_utils.ModelWeights.from_model(keras_model)
    # Assert the initial state weights are not the same as the pretrained model.
    initial_weights = fedavg.get_model_weights(state)
    self.assertNotAllClose(
        tf.nest.flatten(pretrained_weights), tf.nest.flatten(initial_weights))
    # Change the state weights to those from our pretrained model.
    state = fedavg.set_model_weights(state, pretrained_weights)
    self.assertAllClose(
        tf.nest.flatten(pretrained_weights),
        tf.nest.flatten(fedavg.get_model_weights(state)))
    # Run some FedAvg.
    client_data = [self._test_data()] * 3  # 3 clients with identical data.
    for _ in range(3):
      fedavg_result = fedavg.next(state, client_data)
      state = fedavg_result.state
    # Weights should be different after training.
    self.assertNotAllClose(
        tf.nest.flatten(pretrained_weights),
        tf.nest.flatten(fedavg.get_model_weights(state)))
    # We should be able to assign the back to the keras model without raising
    # an error.
    fedavg.get_model_weights(state).assign_weights_to(keras_model)

  def test_created_model_raises(self):
    with self.assertRaises(TypeError):
      composers.build_basic_fedavg_process(model_examples.LinearRegression(),
                                           0.1)

  @parameterized.named_parameters(('int', 1),
                                  ('optimizer', sgdm.build_sgdm(0.1)))
  def test_wrong_client_learning_rate_raises(self, bad_client_lr):
    with self.assertRaises(TypeError):
      composers.build_basic_fedavg_process(model_examples.LinearRegression(),
                                           bad_client_lr)


if __name__ == '__main__':
  execution_contexts.set_local_python_execution_context()
  tf.test.main()
