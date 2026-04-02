"""
NexusFlow Customer Success Digital FTE - Message Processor (Agent Worker)
==========================================================================
Exercise 2.3: Kafka Event Streaming - Main Agent Worker

This is the CORE of the production architecture - the 24/7 autonomous
Digital FTE agent that processes customer support messages.

What This Does:
1. Consumes messages from Kafka "customer-support-tickets" topic
2. Loads the OpenAI Agent with production tools and prompts
3. Retrieves customer context from PostgreSQL (conversation history, sentiment)
4. Runs the agent to generate intelligent responses
5. Saves all interactions to PostgreSQL (conversations, messages, tickets, metrics)
6. Calls the appropriate channel handler to send the reply
7. Handles errors gracefully with structured logging

This creates a fully autonomous customer support agent that runs continuously,
processing messages from all channels (Email, WhatsApp, Web Form) through a
unified event stream.

Author: Digital FTE Team
Version: 1.0.0 (Production)
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from contextlib import asynccontextmanager

# Async Kafka client
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError

# Database connection
import asyncpg

# OpenAI Agents SDK
from agents import Runner

# Local imports - Production tools and prompts
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.tools import (
    search_knowledge_base,
    create_ticket,
    get_customer_history,
    escalate_to_human,
    send_response,
)

from agent.prompts import CUSTOMER_SUCCESS_SYSTEM_PROMPT

# Channel handlers for sending responses
from channels.gmail_handler import GmailClient, EmailResponseSender
from channels.whatsapp_handler import TwilioWhatsAppClient, WhatsAppResponseSender

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    """Application configuration from environment variables."""
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'customer-support-tickets')
    KAFKA_CONSUMER_GROUP = os.getenv('KAFKA_CONSUMER_GROUP', 'digital-fte-agent')
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/nexusflow')
    
    # OpenAI
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')
    
    # Processing
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY = float(os.getenv('RETRY_DELAY', '1.0'))
    BATCH_SIZE = int(os.getenv('KAFKA_BATCH_SIZE', '100'))
    POLL_TIMEOUT = float(os.getenv('KAFKA_POLL_TIMEOUT', '1000'))  # ms
    
    # Channel APIs
    GMAIL_SERVICE_ACCOUNT = os.getenv('GMAIL_SERVICE_ACCOUNT_FILE', '')
    GMAIL_DELEGATED_EMAIL = os.getenv('GMAIL_DELEGATED_EMAIL', '')
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
    TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER', '')


# =============================================================================
# DATABASE CONNECTION POOL
# =============================================================================

class DatabasePool:
    """
    Manages PostgreSQL connection pool for the agent worker.
    
    Provides efficient connection reuse for high-throughput processing.
    """
    
    _pool: Optional[asyncpg.Pool] = None

    @classmethod
    async def create_pool(cls, database_url: str, min_size: int = 5, max_size: int = 20):
        """
        Create the connection pool.

        Args:
            database_url: PostgreSQL connection string
            min_size: Minimum connections in pool
            max_size: Maximum connections in pool
        """
        if cls._pool is None:
            # Strip '+asyncpg' from URL for raw asyncpg (SQLAlchemy -> asyncpg compatibility)
            clean_url = database_url.replace('+asyncpg', '', 1) if '+asyncpg' in database_url else database_url
            cls._pool = await asyncpg.create_pool(
                clean_url,
                min_size=min_size,
                max_size=max_size,
                command_timeout=60
            )
            logger.info(f"Database pool created: min={min_size}, max={max_size}")
    
    @classmethod
    async def get_pool(cls) -> asyncpg.Pool:
        """Get the connection pool."""
        if cls._pool is None:
            raise RuntimeError("Database pool not initialized. Call create_pool first.")
        return cls._pool
    
    @classmethod
    async def close_pool(cls):
        """Close the connection pool."""
        if cls._pool:
            await cls._pool.close()
            cls._pool = None
            logger.info("Database pool closed")
    
    @classmethod
    @asynccontextmanager
    async def acquire(cls):
        """
        Context manager for acquiring a connection from the pool.
        
        Usage:
            async with DatabasePool.acquire() as conn:
                await conn.fetch(...)
        """
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            yield conn


# =============================================================================
# OPENAI AGENT RUNNER
# =============================================================================

class DigitalFTEAgent:
    """
    OpenAI Agent runner for the Digital FTE.
    
    Loads production tools and prompts, runs the agent with customer context,
    and returns the generated response.
    """
    
    def __init__(self):
        """Initialize the agent runner."""
        self._runner: Optional[Runner] = None
        self._tools = [
            search_knowledge_base,
            create_ticket,
            get_customer_history,
            escalate_to_human,
            send_response,
        ]
    
    async def initialize(self):
        """Initialize the OpenAI Agent runner."""
        if not Config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        # The Runner will use the @function_tool decorated functions
        self._runner = Runner(
            name="NexusFlow Customer Success Digital FTE",
            instructions=CUSTOMER_SUCCESS_SYSTEM_PROMPT,
            tools=self._tools,
            model=Config.OPENAI_MODEL
        )
        
        logger.info("Digital FTE Agent initialized")
    
    async def process_message(
        self,
        customer_message: str,
        customer_context: Dict[str, Any],
        channel: str
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Process a customer message through the AI agent.
        
        Args:
            customer_message: The customer's message content
            customer_context: Customer profile and conversation history
            channel: Communication channel
            
        Returns:
            Tuple of (response_text, metadata)
        """
        if self._runner is None:
            await self.initialize()
        
        # Build the user message with context
        user_message = self._build_user_message(
            customer_message,
            customer_context,
            channel
        )
        
        # Run the agent
        result = await self._runner.run(user_message)
        
        # Extract response and metadata
        response_text = result.final_output
        metadata = {
            "model": Config.OPENAI_MODEL,
            "tokens_used": getattr(result, 'usage', {}).get('total_tokens', 0),
            "tool_calls": len(result.tool_calls) if hasattr(result, 'tool_calls') else 0
        }
        
        logger.info(
            f"Agent processed message: tokens={metadata['tokens_used']}, "
            f"tool_calls={metadata['tool_calls']}"
        )
        
        return response_text, metadata
    
    def _build_user_message(
        self,
        message: str,
        context: Dict[str, Any],
        channel: str
    ) -> str:
        """
        Build the user message with full context for the agent.
        
        Args:
            message: Customer message
            context: Customer and conversation context
            channel: Communication channel
            
        Returns:
            Formatted message for the agent
        """
        context_parts = []
        
        # Customer info
        if context.get('customer_name'):
            context_parts.append(f"Customer: {context['customer_name']}")
        if context.get('customer_email'):
            context_parts.append(f"Email: {context['customer_email']}")
        if context.get('plan'):
            context_parts.append(f"Plan: {context['plan']}")
        if context.get('is_vip'):
            context_parts.append(f"VIP: {context['is_vip']}")
        
        # Conversation context
        if context.get('conversation_history'):
            history = context['conversation_history']
            context_parts.append(f"\nPrevious Messages: {len(history)}")
            for msg in history[-3:]:  # Last 3 messages
                context_parts.append(f"  - {msg.get('content', '')[:100]}...")
        
        # Sentiment context
        if context.get('current_sentiment'):
            context_parts.append(f"\nCurrent Sentiment: {context['current_sentiment']}")
        if context.get('sentiment_trend'):
            context_parts.append(f"Sentiment Trend: {context['sentiment_trend']}")
        
        # Channel context
        context_parts.append(f"\nChannel: {channel}")
        
        # Build final message
        full_message = f"""
CONTEXT:
{chr(10).join(context_parts)}

CUSTOMER MESSAGE:
{message}

Please respond according to the system instructions.
"""
        return full_message


# =============================================================================
# KAFKA CONSUMER + MESSAGE PROCESSOR
# =============================================================================

class MessageProcessor:
    """
    Main message processor that consumes from Kafka and runs the Digital FTE agent.
    
    This is the 24/7 autonomous worker that:
    1. Consumes messages from Kafka
    2. Loads customer context from database
    3. Runs the AI agent
    4. Saves results to database
    5. Sends response via appropriate channel
    """
    
    def __init__(self):
        """Initialize the message processor."""
        self._consumer: Optional[AIOKafkaConsumer] = None
        self._agent: Optional[DigitalFTEAgent] = None
        self._is_running = False
        
        # Channel clients (lazy initialized)
        self._gmail_client: Optional[GmailClient] = None
        self._twilio_client: Optional[TwilioWhatsAppClient] = None
    
    async def start(self):
        """Start the message processor."""
        logger.info("Starting Message Processor...")
        
        # Initialize database pool
        await DatabasePool.create_pool(Config.DATABASE_URL)
        
        # Initialize Kafka consumer
        self._consumer = AIOKafkaConsumer(
            Config.KAFKA_TOPIC,
            bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS.split(','),
            group_id=Config.KAFKA_CONSUMER_GROUP,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            max_poll_records=Config.BATCH_SIZE
        )
        await self._consumer.start()
        logger.info(f"Kafka consumer started, listening to {Config.KAFKA_TOPIC}")
        
        # Initialize agent
        self._agent = DigitalFTEAgent()
        await self._agent.initialize()
        
        self._is_running = True
        logger.info("Message Processor started successfully")
    
    async def stop(self):
        """Stop the message processor."""
        self._is_running = False
        
        if self._consumer:
            await self._consumer.stop()
            logger.info("Kafka consumer stopped")
        
        await DatabasePool.close_pool()
        logger.info("Message Processor stopped")
    
    async def run(self):
        """
        Main processing loop - runs continuously.
        
        This is the heart of the 24/7 autonomous Digital FTE.
        """
        logger.info("Entering main processing loop...")
        
        while self._is_running:
            try:
                # Poll for messages from Kafka
                messages = await self._consumer.getmany(
                    timeout_ms=Config.POLL_TIMEOUT,
                    max_records=Config.BATCH_SIZE
                )
                
                # Process each message
                for topic_partition, records in messages.items():
                    for record in records:
                        await self._process_kafka_message(record)
                
                # Small delay to prevent tight loop when no messages
                if not messages:
                    await asyncio.sleep(0.1)
                    
            except KafkaError as e:
                logger.error(f"Kafka error in processing loop: {e}")
                await asyncio.sleep(1.0)  # Back off on error
                
            except Exception as e:
                logger.error(f"Unexpected error in processing loop: {e}", exc_info=True)
                await asyncio.sleep(1.0)
        
        logger.info("Processing loop exited")
    
    async def _process_kafka_message(self, record):
        """
        Process a single Kafka message.
        
        Args:
            record: Kafka consumer record
        """
        event_id = "unknown"
        
        try:
            # Parse event from Kafka record
            event = json.loads(record.value.decode('utf-8'))
            event_id = event.get('event_id', 'unknown')
            
            logger.info(f"Processing event: {event_id} | type={event.get('event_type')}")
            
            # Extract event data
            customer_id = event.get('customer_id')
            channel = event.get('channel')
            message_content = event.get('message_content')
            message_id = event.get('message_id')
            
            if not all([customer_id, channel, message_content]):
                logger.warning(f"Invalid event {event_id}: missing required fields")
                return
            
            # Load customer context from database
            customer_context = await self._load_customer_context(customer_id)
            
            # Run the AI agent
            response_text, agent_metadata = await self._agent.process_message(
                customer_message=message_content,
                customer_context=customer_context,
                channel=channel
            )
            
            # Save conversation to database
            await self._save_conversation(
                event=event,
                response_text=response_text,
                agent_metadata=agent_metadata
            )
            
            # Send response via appropriate channel
            await self._send_channel_response(
                channel=channel,
                customer_id=customer_id,
                response_text=response_text,
                event=event
            )
            
            logger.info(f"Event {event_id} processed successfully")
            
        except Exception as e:
            logger.error(
                f"Error processing event {event_id}: {e}",
                exc_info=True,
                extra={'event_id': event_id}
            )
            # Could send to error queue here
    
    async def _load_customer_context(self, customer_id: str) -> Dict[str, Any]:
        """
        Load customer context from database.
        
        Args:
            customer_id: Customer identifier
            
        Returns:
            Customer context dictionary
        """
        async with DatabasePool.acquire() as conn:
            # Get customer profile
            customer = await conn.fetchrow("""
                SELECT id, name, email, phone, company, plan, is_vip,
                       current_sentiment, sentiment_trend, total_conversations
                FROM customers
                WHERE email = $1 OR phone = $1
            """, customer_id)
            
            if not customer:
                # New customer - return minimal context
                return {
                    'customer_id': customer_id,
                    'is_new_customer': True
                }
            
            # Get recent conversation history
            history = await conn.fetch("""
                SELECT m.content, m.direction, m.sentiment, m.created_at
                FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                WHERE c.customer_id = $1
                ORDER BY m.created_at DESC
                LIMIT 10
            """, customer['id'])
            
            return {
                'customer_id': str(customer['id']),
                'customer_name': customer['name'],
                'customer_email': customer['email'],
                'company': customer['company'],
                'plan': customer['plan'],
                'is_vip': customer['is_vip'],
                'current_sentiment': customer['current_sentiment'],
                'sentiment_trend': customer['sentiment_trend'],
                'total_conversations': customer['total_conversations'],
                'is_new_customer': False,
                'conversation_history': [
                    {'content': h['content'], 'direction': h['direction'], 'sentiment': h['sentiment']}
                    for h in reversed(history)
                ]
            }
    
    async def _save_conversation(
        self,
        event: Dict[str, Any],
        response_text: str,
        agent_metadata: Dict[str, Any]
    ):
        """
        Save conversation to database.
        
        Args:
            event: Original Kafka event
            response_text: AI-generated response
            agent_metadata: Agent processing metadata
        """
        async with DatabasePool.acquire() as conn:
            async with conn.transaction():
                # Get or create customer
                customer_result = await conn.fetchrow("""
                    SELECT id FROM customers
                    WHERE email = $1 OR phone = $1
                """, event.get('customer_email') or event.get('customer_id'))
                
                if not customer_result:
                    # Create new customer
                    customer_result = await conn.fetchrow("""
                        INSERT INTO customers (name, email, phone, company, plan)
                        VALUES ($1, $2, $3, $4, 'free')
                        RETURNING id
                    """,
                        event.get('customer_name', 'Unknown'),
                        event.get('customer_email'),
                        event.get('customer_phone'),
                        event.get('channel_metadata', {}).get('company')
                    )
                
                customer_id = customer_result['id']
                
                # Create or get conversation
                conversation_id = event.get('conversation_id')
                if not conversation_id:
                    conv_result = await conn.fetchrow("""
                        INSERT INTO conversations (
                            customer_id, original_channel, current_channel,
                            subject, initial_sentiment, current_sentiment,
                            first_message_at, last_message_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
                        RETURNING id
                    """,
                        customer_id,
                        event.get('channel'),
                        event.get('channel'),
                        event.get('message_subject'),
                        'neutral',  # Would come from sentiment analysis
                        'neutral'
                    )
                    conversation_id = conv_result['id']
                
                # Save inbound message (customer)
                await conn.execute("""
                    INSERT INTO messages (
                        conversation_id, direction, content, channel,
                        sentiment, is_ai_generated, created_at
                    ) VALUES ($1, 'inbound', $2, $3, $4, FALSE, NOW())
                """,
                    conversation_id,
                    event.get('message_content'),
                    event.get('channel'),
                    'neutral'  # Would come from sentiment analysis
                )
                
                # Save outbound message (AI response)
                await conn.execute("""
                    INSERT INTO messages (
                        conversation_id, direction, content, channel,
                        sentiment, is_ai_generated, ai_model, ai_tokens_used,
                        created_at
                    ) VALUES ($1, 'outbound', $2, $3, $4, TRUE, $5, $6, NOW())
                """,
                    conversation_id,
                    response_text,
                    event.get('channel'),
                    'neutral',
                    agent_metadata.get('model', Config.OPENAI_MODEL),
                    agent_metadata.get('tokens_used', 0)
                )
                
                # Update conversation
                await conn.execute("""
                    UPDATE conversations
                    SET message_count = message_count + 1,
                        last_message_at = NOW(),
                        updated_at = NOW()
                    WHERE id = $1
                """, conversation_id)
                
                # Update customer metrics
                await conn.execute("""
                    UPDATE customers
                    SET total_messages = total_messages + 1,
                        last_interaction_at = NOW(),
                        updated_at = NOW()
                    WHERE id = $1
                """, customer_id)
        
        logger.info(f"Conversation saved: customer={customer_id}, conv={conversation_id}")
    
    async def _send_channel_response(
        self,
        channel: str,
        customer_id: str,
        response_text: str,
        event: Dict[str, Any]
    ):
        """
        Send response via the appropriate channel.
        
        Args:
            channel: Communication channel
            customer_id: Customer identifier
            response_text: Response to send
            event: Original Kafka event
        """
        try:
            if channel == 'email':
                await self._send_email_response(
                    to_email=event.get('customer_email'),
                    subject=f"Re: {event.get('message_subject', 'Support Request')}",
                    message=response_text,
                    thread_id=event.get('thread_id')
                )
            elif channel == 'whatsapp':
                await self._send_whatsapp_response(
                    to_number=event.get('customer_phone') or customer_id,
                    message=response_text
                )
            elif channel == 'web_form':
                # Web form responses are typically sent via email
                await self._send_email_response(
                    to_email=event.get('customer_email'),
                    subject=f"Re: {event.get('message_subject', 'Support Request')}",
                    message=response_text
                )
            else:
                logger.warning(f"Unknown channel: {channel}")
                
        except Exception as e:
            logger.error(f"Failed to send channel response: {e}", exc_info=True)
    
    async def _send_email_response(
        self,
        to_email: str,
        subject: str,
        message: str,
        thread_id: Optional[str] = None
    ):
        """Send email response via Gmail API."""
        if not self._gmail_client:
            if Config.GMAIL_SERVICE_ACCOUNT and Config.GMAIL_DELEGATED_EMAIL:
                self._gmail_client = GmailClient(
                    service_account_file=Config.GMAIL_SERVICE_ACCOUNT,
                    delegated_email=Config.GMAIL_DELEGATED_EMAIL,
                    project_id=os.getenv('GCP_PROJECT_ID', ''),
                    topic_name=''
                )
            else:
                logger.warning("Gmail not configured, skipping email response")
                return
        
        response_sender = EmailResponseSender(self._gmail_client)
        await response_sender.send_response(
            to_email=to_email,
            subject=subject,
            message=message,
            ticket_id="",  # Would get from database
            thread_id=thread_id
        )
    
    async def _send_whatsapp_response(
        self,
        to_number: str,
        message: str
    ):
        """Send WhatsApp response via Twilio API."""
        if not self._twilio_client:
            if Config.TWILIO_ACCOUNT_SID and Config.TWILIO_AUTH_TOKEN:
                self._twilio_client = TwilioWhatsAppClient(
                    account_sid=Config.TWILIO_ACCOUNT_SID,
                    auth_token=Config.TWILIO_AUTH_TOKEN,
                    whatsapp_number=Config.TWILIO_WHATSAPP_NUMBER
                )
            else:
                logger.warning("Twilio not configured, skipping WhatsApp response")
                return
        
        response_sender = WhatsAppResponseSender(self._twilio_client)
        await response_sender.send_response(
            to_number=to_number,
            message=message
        )


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

async def main():
    """
    Main entry point for the Digital FTE Agent Worker.
    
    This runs 24/7, consuming messages from Kafka and processing them
    through the AI agent.
    """
    logger.info("=" * 80)
    logger.info("NEXUSFLOW DIGITAL FTE - AGENT WORKER")
    logger.info("=" * 80)
    logger.info("Starting 24/7 autonomous customer support agent...")
    
    # Validate configuration
    if not Config.OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY is required")
        sys.exit(1)
    
    # Create and start processor
    processor = MessageProcessor()
    
    try:
        await processor.start()
        await processor.run()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await processor.stop()
    
    logger.info("Agent Worker shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
