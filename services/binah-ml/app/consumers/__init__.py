"""Kafka consumers for binah-ml service"""

from .entity_consumer import EntityCreatedConsumer
from .training_trigger import AutoTrainingTrigger

__all__ = ['EntityCreatedConsumer', 'AutoTrainingTrigger']
