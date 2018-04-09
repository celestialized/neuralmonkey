"""Split temporal states such that the sequence is n-times longer."""
from typing import Callable, Set
import tensorflow as tf
from typeguard import check_argument_types

from neuralmonkey.decorators import tensor
from neuralmonkey.dataset import Dataset
from neuralmonkey.model.model_part import ModelPart, FeedDict
from neuralmonkey.model.stateful import TemporalStateful


class SequenceSplitter(TemporalStateful, ModelPart):
    def __init__(
            self,
            parent: TemporalStateful,
            factor: int,
            projection_size: int = None,
            projection_activation: Callable = None) -> None:
        """Initialize SetenceSplitter.

        Args:
            parent: TemporalStateful whose states will be split.
            factor: Factor by which the states will be split - the  resulting
                sequence will be longer by this factor.
        """
        check_argument_types()

        ModelPart.__init__(
            self, name="sequence_split",
            save_checkpoint=None, load_checkpoint=None, initializers=None)
        self.parent = parent
        self.factor = factor
        self.projection_size = projection_size
        self.activation = activation

        state_dim = parent.temporal_states.get_shape()[2].value
        if state_dim % factor != 0:
            raise ValueError((
                "Dimension of the parent temporal stateful ({}) must be "
                "dividable by the given factor ({}).").format(
                    state_dim, factor))

    @tensor
    def temporal_states(self) -> tf.Tensor:
        states = self.parent.temporal_states
        if self.projection_size:
            states = tf.layers.dense(
                states, self.projection_size, activation=self.activation)

        return split_by_factor(self.parent.temporal_states, self.factor)

    @tensor
    def temporal_mask(self) -> tf.Tensor:
        double_mask = tf.stack(
            self.factor * [tf.expand_dims(self.parent.temporal_mask, 2)],
            axis=2)
        return tf.squeeze(split_by_factor(double_mask, self.factor), axis=2)

    def feed_dict(self, dataset: Dataset, train: bool) -> FeedDict:
        return {}

    def get_dependencies(self) -> Set[ModelPart]:
        to_return = set([self])
        to_return = to_return.union(self.parent.get_dependencies())
        return to_return


def split_by_factor(tensor_3d: tf.Tensor, factor: int) -> tf.Tensor:
    orig_shape = tf.shape(tensor_3d)
    batch_size = orig_shape[0]
    max_time = orig_shape[1]
    state_dim = tensor_3d.get_shape()[2].value
    return tf.reshape(
        tensor_3d, [batch_size, max_time * factor, state_dim // factor])