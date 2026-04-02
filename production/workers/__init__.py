"""
NexusFlow Customer Success Digital FTE - Workers Package
=========================================================

This package contains the background workers for the production system.

Modules:
- kafka_producer: Async Kafka event publisher for channel handlers
- message_processor: Main agent worker that consumes from Kafka and runs the AI agent

The workers create the 24/7 autonomous Digital FTE that processes customer
support messages from all channels through a unified event stream.
"""

from .kafka_producer import (
    KafkaEventProducer,
    KafkaProducerContext,
    ChannelEventPublisher,
    UnifiedTicketEvent,
    EventType,
    ChannelType
)

from .message_processor import (
    MessageProcessor,
    DigitalFTEAgent,
    DatabasePool,
    Config,
    main
)

__all__ = [
    # Kafka Producer
    "KafkaEventProducer",
    "KafkaProducerContext",
    "ChannelEventPublisher",
    "UnifiedTicketEvent",
    "EventType",
    "ChannelType",
    
    # Message Processor
    "MessageProcessor",
    "DigitalFTEAgent",
    "DatabasePool",
    "Config",
    "main"
]
