"""
NexusFlow Customer Success Digital FTE - Database Operations
=============================================================
Production database operations for PostgreSQL with asyncpg.

This module provides all database operations needed for the Digital FTE:
- Customer management (get/create/update)
- Conversation tracking
- Message persistence
- Ticket CRUD operations
- Escalation records
- Knowledge base search (with pgvector)
- Metrics and reporting

Author: Digital FTE Team
Version: 1.0.0 (Production)
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from contextlib import asynccontextmanager

import asyncpg
from asyncpg import Pool, Record

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# DATABASE MANAGER
# =============================================================================

class DatabaseManager:
    """
    Manages PostgreSQL database connections and operations.

    Uses asyncpg for high-performance async database access.
    """

    _instance: Optional['DatabaseManager'] = None
    _pool: Optional[Pool] = None
    _connected: bool = False

    def __new__(cls):
        """Singleton pattern - ensure only one instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def pool(self) -> Optional[Pool]:
        """Get the connection pool."""
        return self._pool

    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._connected

    async def create_pool(
        self,
        database_url: str,
        min_size: int = 5,
        max_size: int = 20
    ) -> Pool:
        """
        Create database connection pool.

        Args:
            database_url: PostgreSQL connection URL (postgresql://...)
            min_size: Minimum connections in pool
            max_size: Maximum connections in pool

        Returns:
            Connection pool
        """
        if self._pool is not None:
            logger.warning("Connection pool already exists")
            return self._pool

        # Convert sqlalchemy URL to asyncpg format if needed
        if database_url.startswith('postgresql+asyncpg://'):
            database_url = database_url.replace('postgresql+asyncpg://', 'postgresql://')
        elif database_url.startswith('postgresql://'):
            pass  # Already correct format
        else:
            logger.warning(f"Unknown database URL format: {database_url}")

        try:
            self._pool = await asyncpg.create_pool(
                database_url,
                min_size=min_size,
                max_size=max_size,
                command_timeout=60
            )

            # Test connection
            async with self._pool.acquire() as conn:
                await conn.fetchval('SELECT 1')

            self._connected = True
            logger.info(f"✅ Database pool created: {min_size}-{max_size} connections")
            return self._pool

        except Exception as e:
            logger.error(f"❌ Failed to create database pool: {e}")
            self._connected = False
            raise

    async def close_pool(self):
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            self._connected = False
            logger.info("✅ Database pool closed")

    @asynccontextmanager
    async def acquire(self):
        """Acquire a connection from the pool."""
        if not self._pool:
            raise RuntimeError("Database pool not initialized")

        async with self._pool.acquire() as conn:
            yield conn


# Global database manager instance
db_manager = DatabaseManager()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

async def init_database(database_url: str):
    """Initialize database connection pool."""
    return await db_manager.create_pool(database_url)


async def close_database():
    """Close database connection pool."""
    await db_manager.close_pool()


@asynccontextmanager
async def get_db_connection():
    """Get a database connection from the pool."""
    async with db_manager.acquire() as conn:
        yield conn


def is_db_connected() -> bool:
    """Check if database is connected."""
    return db_manager.is_connected


# =============================================================================
# CUSTOMER OPERATIONS
# =============================================================================

async def get_customer_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Get customer by email address.
    
    Args:
        email: Customer email
        
    Returns:
        Customer data or None
    """
    async with get_db_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT * FROM customers
            WHERE email = $1
            """,
            email
        )
        
        if row:
            return dict(row)
        return None


async def get_customer_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    """
    Get customer by phone number.
    
    Args:
        phone: Customer phone number
        
    Returns:
        Customer data or None
    """
    async with get_db_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT * FROM customers
            WHERE phone = $1
            """,
            phone
        )
        
        if row:
            return dict(row)
        return None


async def create_customer(
    name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    plan: str = 'free',
    is_vip: bool = False
) -> str:
    """
    Create a new customer.
    
    Args:
        name: Customer name
        email: Customer email
        phone: Customer phone
        company: Company name
        plan: Subscription plan
        is_vip: Whether customer is VIP
        
    Returns:
        Customer ID (UUID)
    """
    async with get_db_connection() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO customers (name, email, phone, company, plan, is_vip)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
            """,
            name, email, phone, company, plan, is_vip
        )
        
        customer_id = str(row['id'])
        logger.info(f"Created customer: {customer_id} ({email})")
        return customer_id


async def get_or_create_customer(
    name: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    company: Optional[str] = None
) -> Tuple[str, bool]:
    """
    Get existing customer or create new one.
    
    Args:
        name: Customer name
        email: Customer email
        phone: Customer phone
        company: Company name
        
    Returns:
        Tuple of (customer_id, is_new_customer)
    """
    # Try to find by email
    if email:
        customer = await get_customer_by_email(email)
        if customer:
            return str(customer['id']), False
    
    # Try to find by phone
    if phone:
        customer = await get_customer_by_phone(phone)
        if customer:
            return str(customer['id']), False
    
    # Create new customer
    customer_id = await create_customer(
        name=name,
        email=email,
        phone=phone,
        company=company,
        plan='free',
        is_vip=False
    )
    
    return customer_id, True


async def update_customer_sentiment(
    customer_id: str,
    sentiment: str,
    sentiment_trend: str = 'stable'
):
    """
    Update customer's current sentiment.
    
    Args:
        customer_id: Customer ID
        sentiment: New sentiment value
        sentiment_trend: Sentiment trend
    """
    async with get_db_connection() as conn:
        await conn.execute(
            """
            UPDATE customers
            SET current_sentiment = $2,
                sentiment_trend = $3,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            """,
            customer_id, sentiment, sentiment_trend
        )


# =============================================================================
# CONVERSATION OPERATIONS
# =============================================================================

async def create_conversation(
    customer_id: str,
    subject: str,
    channel: str,
    initial_sentiment: Optional[str] = None
) -> str:
    """
    Create a new conversation.
    
    Args:
        customer_id: Customer ID
        subject: Conversation subject
        channel: Communication channel
        initial_sentiment: Initial sentiment
        
    Returns:
        Conversation ID (UUID)
    """
    async with get_db_connection() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO conversations (
                customer_id, subject, original_channel, current_channel,
                initial_sentiment, current_sentiment, status
            )
            VALUES ($1, $2, $3, $4, $5, $6, 'open')
            RETURNING id
            """,
            customer_id, subject, channel, channel, initial_sentiment, initial_sentiment
        )
        
        conversation_id = str(row['id'])
        logger.info(f"Created conversation: {conversation_id}")
        return conversation_id


async def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    """
    Get conversation by ID.
    
    Args:
        conversation_id: Conversation ID
        
    Returns:
        Conversation data or None
    """
    async with get_db_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT * FROM conversations
            WHERE id = $1
            """,
            conversation_id
        )
        
        if row:
            return dict(row)
        return None


async def get_customer_conversations(
    customer_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get customer's recent conversations.
    
    Args:
        customer_id: Customer ID
        limit: Number of conversations to return
        
    Returns:
        List of conversations
    """
    async with get_db_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM conversations
            WHERE customer_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            customer_id, limit
        )
        
        return [dict(row) for row in rows]


async def update_conversation_status(
    conversation_id: str,
    status: str,
    is_resolved: bool = False,
    resolution_summary: Optional[str] = None
):
    """
    Update conversation status.
    
    Args:
        conversation_id: Conversation ID
        status: New status
        is_resolved: Whether resolved
        resolution_summary: Resolution summary
    """
    async with get_db_connection() as conn:
        await conn.execute(
            """
            UPDATE conversations
            SET status = $2,
                is_resolved = $3,
                resolution_summary = $4,
                resolved_at = CASE WHEN $3 THEN CURRENT_TIMESTAMP ELSE resolved_at END,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            """,
            conversation_id, status, is_resolved, resolution_summary
        )


# =============================================================================
# MESSAGE OPERATIONS
# =============================================================================

async def create_message(
    conversation_id: str,
    content: str,
    direction: str,
    channel: str,
    sentiment: Optional[str] = None,
    is_ai_generated: bool = False,
    ai_model: Optional[str] = None,
    ai_confidence: Optional[float] = None,
    ai_tokens_used: Optional[int] = None,
    subject: Optional[str] = None
) -> str:
    """
    Create a new message.
    
    Args:
        conversation_id: Conversation ID
        content: Message content
        direction: 'inbound' or 'outbound'
        channel: Communication channel
        sentiment: Message sentiment
        is_ai_generated: Whether AI-generated
        ai_model: AI model used
        ai_confidence: AI confidence score
        ai_tokens_used: Tokens used
        subject: Message subject
        
    Returns:
        Message ID (UUID)
    """
    async with get_db_connection() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO messages (
                conversation_id, content, direction, channel,
                sentiment, is_ai_generated, ai_model, ai_confidence,
                ai_tokens_used, subject
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id, created_at
            """,
            conversation_id, content, direction, channel,
            sentiment, is_ai_generated, ai_model, ai_confidence,
            ai_tokens_used, subject
        )
        
        message_id = str(row['id'])
        
        # Update conversation message count
        await conn.execute(
            """
            UPDATE conversations
            SET message_count = message_count + 1,
                last_message_at = CURRENT_TIMESTAMP,
                current_sentiment = COALESCE($2, current_sentiment)
            WHERE id = $1
            """,
            conversation_id, sentiment
        )
        
        logger.info(f"Created message: {message_id}")
        return message_id


async def get_conversation_messages(
    conversation_id: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get messages for a conversation.
    
    Args:
        conversation_id: Conversation ID
        limit: Number of messages to return
        
    Returns:
        List of messages
    """
    async with get_db_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM messages
            WHERE conversation_id = $1
            ORDER BY created_at ASC
            LIMIT $2
            """,
            conversation_id, limit
        )
        
        return [dict(row) for row in rows]


# =============================================================================
# TICKET OPERATIONS
# =============================================================================

async def create_ticket(
    ticket_id: str,
    conversation_id: str,
    customer_id: str,
    subject: str,
    description: str,
    channel: str,
    priority: str = 'medium',
    status: str = 'open'
) -> str:
    """
    Create a new support ticket.
    
    Args:
        ticket_id: Human-readable ticket ID
        conversation_id: Linked conversation ID
        customer_id: Customer ID
        subject: Ticket subject
        description: Ticket description
        channel: Communication channel
        priority: Ticket priority
        status: Ticket status
        
    Returns:
        Ticket ID
    """
    async with get_db_connection() as conn:
        await conn.execute(
            """
            INSERT INTO tickets (
                id, conversation_id, customer_id, subject, description,
                channel, priority, status, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, CURRENT_TIMESTAMP)
            """,
            ticket_id, conversation_id, customer_id, subject, description,
            channel, priority, status
        )
        
        logger.info(f"Created ticket: {ticket_id}")
        return ticket_id


async def get_ticket(ticket_id: str) -> Optional[Dict[str, Any]]:
    """
    Get ticket by ID.
    
    Args:
        ticket_id: Ticket ID
        
    Returns:
        Ticket data or None
    """
    async with get_db_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT * FROM tickets
            WHERE id = $1
            """,
            ticket_id
        )
        
        if row:
            return dict(row)
        return None


async def update_ticket_status(
    ticket_id: str,
    status: str,
    resolved_by: Optional[str] = None,
    resolution_summary: Optional[str] = None
):
    """
    Update ticket status.
    
    Args:
        ticket_id: Ticket ID
        status: New status
        resolved_by: Who resolved it
        resolution_summary: Resolution summary
    """
    async with get_db_connection() as conn:
        await conn.execute(
            """
            UPDATE tickets
            SET status = $2,
                resolved_at = CASE WHEN $2 IN ('resolved', 'closed') THEN CURRENT_TIMESTAMP ELSE resolved_at END,
                resolved_by = $3,
                resolution_summary = $4,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
            """,
            ticket_id, status, resolved_by, resolution_summary
        )


async def get_tickets_by_customer(
    customer_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get customer's tickets.
    
    Args:
        customer_id: Customer ID
        limit: Number of tickets to return
        
    Returns:
        List of tickets
    """
    async with get_db_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT * FROM tickets
            WHERE customer_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            customer_id, limit
        )
        
        return [dict(row) for row in rows]


# =============================================================================
# KNOWLEDGE BASE OPERATIONS
# =============================================================================

async def search_knowledge_base(
    query: str,
    limit: int = 3
) -> List[Dict[str, Any]]:
    """
    Search knowledge base using full-text search.
    
    Args:
        query: Search query
        limit: Number of results
        
    Returns:
        List of articles
    """
    async with get_db_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT key, title, content, category, tags, keywords,
                   ts_rank(to_tsvector('english', title || ' ' || content), plainto_tsquery('english', $1)) as rank
            FROM knowledge_base
            WHERE status = 'published'
              AND to_tsvector('english', title || ' ' || content) @@ plainto_tsquery('english', $1)
            ORDER BY rank DESC
            LIMIT $2
            """,
            query, limit
        )
        
        return [dict(row) for row in rows]


async def get_knowledge_base_article(key: str) -> Optional[Dict[str, Any]]:
    """
    Get knowledge base article by key.
    
    Args:
        key: Article key
        
    Returns:
        Article data or None
    """
    async with get_db_connection() as conn:
        row = await conn.fetchrow(
            """
            SELECT * FROM knowledge_base
            WHERE key = $1 AND status = 'published'
            """,
            key
        )
        
        if row:
            return dict(row)
        return None


# =============================================================================
# METRICS OPERATIONS
# =============================================================================

async def get_dashboard_metrics() -> Dict[str, Any]:
    """
    Get dashboard metrics.
    
    Returns:
        Dashboard metrics dictionary
    """
    async with get_db_connection() as conn:
        # Total tickets
        total_tickets = await conn.fetchval("SELECT COUNT(*) FROM tickets")
        
        # Tickets by status
        status_rows = await conn.fetch(
            "SELECT status, COUNT(*) as count FROM tickets GROUP BY status"
        )
        tickets_by_status = {row['status']: row['count'] for row in status_rows}
        
        # Tickets by channel
        channel_rows = await conn.fetch(
            "SELECT channel, COUNT(*) as count FROM tickets GROUP BY channel"
        )
        tickets_by_channel = {row['channel']: row['count'] for row in channel_rows}
        
        # Tickets by priority
        priority_rows = await conn.fetch(
            "SELECT priority, COUNT(*) as count FROM tickets GROUP BY priority"
        )
        tickets_by_priority = {row['priority']: row['count'] for row in priority_rows}
        
        # Sentiment distribution (from customers)
        sentiment_rows = await conn.fetch(
            "SELECT current_sentiment, COUNT(*) as count FROM customers GROUP BY current_sentiment"
        )
        sentiment_distribution = {row['current_sentiment']: row['count'] for row in sentiment_rows}
        
        # Recent tickets
        recent_rows = await conn.fetch(
            """
            SELECT id, subject, status, priority, channel, created_at
            FROM tickets
            ORDER BY created_at DESC
            LIMIT 10
            """
        )
        recent_tickets = [dict(row) for row in recent_rows]
        
        # AI resolution rate
        ai_resolved = await conn.fetchval(
            "SELECT COUNT(*) FROM tickets WHERE resolved_by = 'AI' OR resolved_by LIKE '%AI%'"
        )
        ai_resolution_rate = (ai_resolved / total_tickets * 100) if total_tickets > 0 else 0
        
        return {
            'total_tickets': total_tickets or 0,
            'tickets_by_status': tickets_by_status,
            'tickets_by_channel': tickets_by_channel,
            'tickets_by_priority': tickets_by_priority,
            'sentiment_distribution': sentiment_distribution,
            'recent_tickets': recent_tickets,
            'ai_resolved_count': ai_resolved or 0,
            'ai_resolution_rate': round(ai_resolution_rate, 2)
        }


async def get_daily_sentiment_report(
    days: int = 7
) -> List[Dict[str, Any]]:
    """
    Get daily sentiment report.
    
    Args:
        days: Number of days to include
        
    Returns:
        Daily sentiment data
    """
    async with get_db_connection() as conn:
        rows = await conn.fetch(
            """
            SELECT 
                DATE(created_at) as date,
                current_sentiment,
                COUNT(*) as count
            FROM customers
            WHERE created_at >= CURRENT_DATE - INTERVAL '%s days'
            GROUP BY DATE(created_at), current_sentiment
            ORDER BY date DESC, count DESC
            """ % days
        )
        
        # Group by date
        report = {}
        for row in rows:
            date_str = str(row['date'])
            if date_str not in report:
                report[date_str] = {
                    'date': date_str,
                    'sentiments': {}
                }
            report[date_str]['sentiments'][row['current_sentiment']] = row['count']
        
        return list(report.values())


# =============================================================================
# INITIALIZATION
# =============================================================================

async def initialize_schema():
    """
    Initialize database schema.
    
    Reads and executes schema.sql file.
    """
    schema_path = os.path.join(
        os.path.dirname(__file__),
        'schema.sql'
    )
    
    if not os.path.exists(schema_path):
        logger.error(f"Schema file not found: {schema_path}")
        return
    
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    
    # Split by semicolons and execute each statement
    statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
    
    async with get_db_connection() as conn:
        for statement in statements:
            try:
                await conn.execute(statement)
            except Exception as e:
                # Ignore "already exists" errors
                if 'already exists' not in str(e).lower():
                    logger.warning(f"Schema init error (may be OK): {e}")
    
    logger.info("✅ Database schema initialized")


# =============================================================================
# MAIN (Testing)
# =============================================================================

if __name__ == "__main__":
    """Test database operations."""
    
    async def test_db():
        print("=" * 80)
        print("NEXUSFLOW DIGITAL FTE - DATABASE OPERATIONS TEST")
        print("=" * 80)
        
        # Get database URL from environment
        database_url = os.getenv(
            'DATABASE_URL',
            'postgresql://postgres:postgres@localhost:5432/nexusflow'
        )
        
        print(f"\nConnecting to: {database_url}")
        
        try:
            # Initialize
            await init_database(database_url)
            print("✅ Database connected")
            
            # Test customer operations
            print("\n1. Testing customer operations...")
            customer_id, is_new = await get_or_create_customer(
                name="Test User",
                email="test@example.com"
            )
            print(f"   Customer ID: {customer_id}, New: {is_new}")
            
            # Test conversation
            print("\n2. Testing conversation operations...")
            conv_id = await create_conversation(
                customer_id=customer_id,
                subject="Test Conversation",
                channel="web_form"
            )
            print(f"   Conversation ID: {conv_id}")
            
            # Test message
            print("\n3. Testing message operations...")
            msg_id = await create_message(
                conversation_id=conv_id,
                content="Test message content",
                direction="inbound",
                channel="web_form"
            )
            print(f"   Message ID: {msg_id}")
            
            # Test ticket
            print("\n4. Testing ticket operations...")
            ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d')}-TEST"
            await create_ticket(
                ticket_id=ticket_id,
                conversation_id=conv_id,
                customer_id=customer_id,
                subject="Test Ticket",
                description="Test description",
                channel="web_form"
            )
            print(f"   Ticket ID: {ticket_id}")
            
            # Test metrics
            print("\n5. Testing metrics...")
            metrics = await get_dashboard_metrics()
            print(f"   Total tickets: {metrics['total_tickets']}")
            
            print("\n" + "=" * 80)
            print("✅ ALL TESTS PASSED")
            print("=" * 80)
            
        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await close_database()
    
    asyncio.run(test_db())
