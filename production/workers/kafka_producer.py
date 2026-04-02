"""
NexusFlow Customer Success Digital FTE - Kafka Producer
========================================================
Exercise 2.3: Kafka Event Streaming - Producer Helper

This module provides a helper to publish customer support events to Kafka
from channel handlers (Gmail, WhatsApp, Web Form).

Features:
- Async Kafka message publishing with aiokafka
- Unified event schema for all channels
- Connection pooling and retry logic
- Structured logging for audit trail

Author: Digital FTE Team
Version: 1.0.0 (Production)
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# Async Kafka client
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError, KafkaTimeoutError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress aiokafka cluster warnings about topic availability during auto-create
logging.getLogger('aiokafka.cluster').setLevel(logging.ERROR)


# =============================================================================
# EVENT TYPES
# =============================================================================

class EventType(str, Enum):
    """Types of events in the customer support system."""
    NEW_MESSAGE = "new_message"
    FOLLOW_UP = "follow_up"
    ESCALATION_REQUESTED = "escalation_requested"
    RESPONSE_SENT = "response_sent"
    TICKET_CREATED = "ticket_created"
    TICKET_RESOLVED = "ticket_resolved"
    CUSTOMER_IDENTIFIED = "customer_identified"
    SENTIMENT_ANALYZED = "sentiment_analyzed"
    ERROR = "error"


class ChannelType(str, Enum):
    """Supported communication channels."""
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    WEB_FORM = "web_form"


# =============================================================================
# UNIFIED EVENT SCHEMA
# =============================================================================

@dataclass
class UnifiedTicketEvent:
    """
    Unified event schema for all customer support events.
    
    This schema is used across all channels to ensure consistent
    event structure for the Kafka stream.
    """
    
    # Event metadata
    event_id: str
    event_type: str
    event_version: str
    timestamp: str
    
    # Customer identification
    customer_id: str
    customer_email: Optional[str]
    customer_phone: Optional[str]
    customer_name: Optional[str]
    
    # Channel information
    channel: str
    channel_metadata: Dict[str, Any]
    
    # Message content
    message_id: str
    message_content: str
    message_subject: Optional[str]
    in_reply_to: Optional[str]
    
    # Conversation context
    conversation_id: Optional[str]
    thread_id: Optional[str]
    is_follow_up: bool
    
    # Ticket information
    ticket_id: Optional[str]
    priority: str
    category: str
    
    # Processing metadata
    received_at: str
    processed_at: Optional[str]
    source_system: str
    
    # Attachments (if any)
    attachments: List[Dict[str, Any]]
    
    @classmethod
    def create(
        cls,
        event_type: EventType,
        customer_id: str,
        channel: str,
        message_content: str,
        message_id: str,
        source_system: str,
        customer_email: Optional[str] = None,
        customer_phone: Optional[str] = None,
        customer_name: Optional[str] = None,
        message_subject: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        conversation_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        is_follow_up: bool = False,
        ticket_id: Optional[str] = None,
        priority: str = "medium",
        category: str = "other",
        channel_metadata: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> "UnifiedTicketEvent":
        """
        Create a new unified event.
        
        Args:
            event_type: Type of event
            customer_id: Customer identifier
            channel: Communication channel
            message_content: Message body
            message_id: Unique message identifier
            source_system: Origin system (gmail, whatsapp, web_form)
            customer_email: Optional customer email
            customer_phone: Optional customer phone
            customer_name: Optional customer name
            message_subject: Optional message subject
            in_reply_to: Optional In-Reply-To header
            conversation_id: Optional conversation ID
            thread_id: Optional thread ID (Gmail)
            is_follow_up: Whether this is a follow-up message
            ticket_id: Optional ticket ID
            priority: Message priority
            category: Message category
            channel_metadata: Channel-specific metadata
            attachments: List of attachments
            
        Returns:
            New UnifiedTicketEvent instance
        """
        now = datetime.now().isoformat()
        
        return cls(
            event_id=f"evt-{int(time.time() * 1000)}-{os.urandom(4).hex()}",
            event_type=event_type.value,
            event_version="1.0.0",
            timestamp=now,
            customer_id=customer_id,
            customer_email=customer_email,
            customer_phone=customer_phone,
            customer_name=customer_name,
            channel=channel.value if isinstance(channel, ChannelType) else channel,
            channel_metadata=channel_metadata or {},
            message_id=message_id,
            message_content=message_content,
            message_subject=message_subject,
            in_reply_to=in_reply_to,
            conversation_id=conversation_id,
            thread_id=thread_id,
            is_follow_up=is_follow_up,
            ticket_id=ticket_id,
            priority=priority,
            category=category,
            received_at=now,
            processed_at=None,
            source_system=source_system,
            attachments=attachments or []
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for JSON serialization."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert event to JSON string for Kafka."""
        return json.dumps(self.to_dict(), default=str)
    
    def set_processed(self):
        """Mark event as processed with timestamp."""
        self.processed_at = datetime.now().isoformat()


# =============================================================================
# KAFKA PRODUCER
# =============================================================================

class KafkaEventProducer:
    """
    Async Kafka producer for customer support events.
    
    Handles connection management, retries, and structured logging.
    """
    
    def __init__(
        self,
        bootstrap_servers: Optional[str] = None,
        topic: str = "customer-support-tickets",
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        Initialize Kafka producer.
        
        Args:
            bootstrap_servers: Kafka bootstrap servers (comma-separated)
            topic: Default topic for events
            max_retries: Maximum retry attempts on failure
            retry_delay: Delay between retries in seconds
        """
        self.bootstrap_servers = bootstrap_servers or os.getenv(
            'KAFKA_BOOTSTRAP_SERVERS',
            'localhost:9092'
        )
        self.topic = topic
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        self._producer: Optional[AIOKafkaProducer] = None
        self._is_running = False

    async def start(self):
        """Start the Kafka producer connection."""
        if self._producer is None:
            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers.split(','),
                value_serializer=lambda v: v.encode('utf-8') if isinstance(v, str) else json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',  # Wait for all replicas to acknowledge
                request_timeout_ms=60000,  # Increase timeout for topic auto-creation
                connections_max_idle_ms=900000  # Keep connections alive longer
            )
            await self._producer.start()
            self._is_running = True
            logger.info(f"Kafka producer started, connected to {self.bootstrap_servers}")
    
    async def stop(self):
        """Stop the Kafka producer connection."""
        if self._producer and self._is_running:
            await self._producer.stop()
            self._is_running = False
            logger.info("Kafka producer stopped")
    
    async def publish_event(
        self,
        event: UnifiedTicketEvent,
        topic: Optional[str] = None,
        key: Optional[str] = None
    ) -> bool:
        """
        Publish an event to Kafka.
        
        Args:
            event: Event to publish
            topic: Optional topic override
            key: Optional partition key (usually customer_id for ordering)
            
        Returns:
            True if published successfully
        """
        if not self._is_running:
            await self.start()
        
        target_topic = topic or self.topic
        
        # Use customer_id as key for partition ordering
        partition_key = key or event.customer_id
        
        for attempt in range(self.max_retries):
            try:
                # Publish to Kafka
                await self._producer.send_and_wait(
                    topic=target_topic,
                    key=partition_key,
                    value=event.to_json()
                )
                
                logger.info(
                    f"Event published: {event.event_id} | "
                    f"type={event.event_type} | "
                    f"customer={event.customer_id} | "
                    f"channel={event.channel}"
                )
                
                return True
                
            except KafkaTimeoutError as e:
                logger.warning(
                    f"Kafka timeout (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error(f"Failed to publish event after {self.max_retries} attempts")
                    
            except KafkaError as e:
                logger.error(f"Kafka error publishing event: {e}")
                # Log to error tracking system
                await self._log_error_event(event, str(e))
                return False
                
            except Exception as e:
                logger.error(f"Unexpected error publishing event: {e}", exc_info=True)
                return False
        
        return False
    
    async def publish_batch(
        self,
        events: List[UnifiedTicketEvent],
        topic: Optional[str] = None
    ) -> int:
        """
        Publish multiple events in a batch.
        
        Args:
            events: List of events to publish
            topic: Optional topic override
            
        Returns:
            Number of successfully published events
        """
        if not self._is_running:
            await self.start()
        
        target_topic = topic or self.topic
        success_count = 0
        
        try:
            for event in events:
                try:
                    await self._producer.send_and_wait(
                        topic=target_topic,
                        key=event.customer_id,
                        value=event.to_json()
                    )
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to publish event {event.event_id}: {e}")
                    await self._log_error_event(event, str(e))
            
            logger.info(f"Batch publish complete: {success_count}/{len(events)} events")
            
        except Exception as e:
            logger.error(f"Batch publish failed: {e}", exc_info=True)
        
        return success_count
    
    async def _log_error_event(self, event: UnifiedTicketEvent, error: str):
        """
        Log an error event for debugging.
        
        Args:
            event: Original event that failed
            error: Error message
        """
        error_event = UnifiedTicketEvent.create(
            event_type=EventType.ERROR,
            customer_id=event.customer_id,
            channel=event.channel,
            message_content=event.message_content,
            message_id=event.message_id,
            source_system=event.source_system,
            customer_email=event.customer_email,
            ticket_id=event.ticket_id,
            channel_metadata={"original_event_id": event.event_id, "error": error}
        )
        
        try:
            await self.publish_event(error_event, topic="customer-support-errors")
        except Exception as e:
            logger.error(f"Failed to log error event: {e}")


# =============================================================================
# CHANNEL-SPECIFIC PUBLISHERS
# =============================================================================

class ChannelEventPublisher:
    """
    Helper class for channel handlers to publish events.
    
    Provides convenience methods for each channel type.
    """
    
    def __init__(self, kafka_producer: KafkaEventProducer):
        """
        Initialize channel event publisher.
        
        Args:
            kafka_producer: KafkaEventProducer instance
        """
        self.kafka_producer = kafka_producer
    
    async def publish_email_event(
        self,
        customer_email: str,
        message_content: str,
        message_id: str,
        subject: str,
        thread_id: str,
        in_reply_to: Optional[str] = None,
        attachments: Optional[List[Dict]] = None
    ) -> bool:
        """
        Publish an email event.
        
        Args:
            customer_email: Sender email address
            message_content: Email body
            message_id: Gmail message ID
            subject: Email subject
            thread_id: Gmail thread ID
            in_reply_to: In-Reply-To header
            attachments: List of attachments
            
        Returns:
            True if published successfully
        """
        event = UnifiedTicketEvent.create(
            event_type=EventType.NEW_MESSAGE,
            customer_id=customer_email,
            channel=ChannelType.EMAIL,
            message_content=message_content,
            message_id=message_id,
            source_system="gmail",
            customer_email=customer_email,
            message_subject=subject,
            thread_id=thread_id,
            in_reply_to=in_reply_to,
            attachments=attachments or [],
            channel_metadata={
                "provider": "gmail",
                "has_attachments": bool(attachments)
            }
        )
        
        return await self.kafka_producer.publish_event(event)
    
    async def publish_whatsapp_event(
        self,
        phone_number: str,
        message_content: str,
        message_id: str,
        media_url: Optional[str] = None,
        media_type: Optional[str] = None
    ) -> bool:
        """
        Publish a WhatsApp event.
        
        Args:
            phone_number: Sender phone number
            message_content: Message text
            message_id: Twilio message SID
            media_url: Optional media URL
            media_type: Optional media type
            
        Returns:
            True if published successfully
        """
        event = UnifiedTicketEvent.create(
            event_type=EventType.NEW_MESSAGE,
            customer_id=phone_number,
            channel=ChannelType.WHATSAPP,
            message_content=message_content,
            message_id=message_id,
            source_system="whatsapp",
            customer_phone=phone_number,
            channel_metadata={
                "provider": "twilio",
                "media_url": media_url,
                "media_type": media_type
            }
        )
        
        return await self.kafka_producer.publish_event(event)
    
    async def publish_web_form_event(
        self,
        customer_email: str,
        customer_name: str,
        message_content: str,
        subject: str,
        ticket_id: str,
        category: str,
        priority: str,
        company: Optional[str] = None,
        phone: Optional[str] = None,
        page_url: Optional[str] = None
    ) -> bool:
        """
        Publish a web form event.
        
        Args:
            customer_email: Submitter email
            customer_name: Submitter name
            message_content: Form description
            subject: Form subject
            ticket_id: Generated ticket ID
            category: Issue category
            priority: Issue priority
            company: Optional company
            phone: Optional phone
            page_url: Optional page URL
            
        Returns:
            True if published successfully
        """
        event = UnifiedTicketEvent.create(
            event_type=EventType.TICKET_CREATED,
            customer_id=customer_email,
            channel=ChannelType.WEB_FORM,
            message_content=message_content,
            message_id=f"webform-{ticket_id}",
            source_system="web_form",
            customer_email=customer_email,
            customer_name=customer_name,
            message_subject=subject,
            ticket_id=ticket_id,
            priority=priority,
            category=category,
            channel_metadata={
                "company": company,
                "phone": phone,
                "page_url": page_url
            }
        )
        
        return await self.kafka_producer.publish_event(event)


# =============================================================================
# CONTEXT MANAGER
# =============================================================================

class KafkaProducerContext:
    """
    Context manager for Kafka producer lifecycle.
    
    Usage:
        async with KafkaProducerContext() as producer:
            await producer.publish_event(event)
    """
    
    def __init__(self, **kwargs):
        """Initialize with Kafka producer kwargs."""
        self.producer = KafkaEventProducer(**kwargs)
    
    async def __aenter__(self) -> KafkaEventProducer:
        """Enter context and start producer."""
        await self.producer.start()
        return self.producer
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context and stop producer."""
        await self.producer.stop()


# =============================================================================
# MAIN (Testing)
# =============================================================================

if __name__ == "__main__":
    """Test Kafka producer."""
    print("=" * 80)
    print("NEXUSFLOW DIGITAL FTE - KAFKA PRODUCER")
    print("=" * 80)
    
    async def test_producer():
        # Check environment
        kafka_servers = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        print(f"\nKafka servers: {kafka_servers}")
        
        # Create producer
        producer = KafkaEventProducer(bootstrap_servers=kafka_servers)
        
        try:
            await producer.start()
            
            # Create test event
            event = UnifiedTicketEvent.create(
                event_type=EventType.NEW_MESSAGE,
                customer_id="test@example.com",
                channel=ChannelType.EMAIL,
                message_content="This is a test message",
                message_id="test-123",
                source_system="test",
                customer_email="test@example.com",
                message_subject="Test Subject"
            )
            
            # Publish event
            success = await producer.publish_event(event)
            print(f"Event published: {success}")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await producer.stop()
        
        print("\n" + "=" * 80)
        print("✅ Kafka producer test complete")
        print("=" * 80)
    
    asyncio.run(test_producer())
