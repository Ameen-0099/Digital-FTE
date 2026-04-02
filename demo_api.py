"""
NexusFlow Customer Success Digital FTE - Demo API with OpenAI + PostgreSQL
===========================================================================
Standalone FastAPI demo with OpenAI Agents SDK integration and PostgreSQL database.

This demo showcases:
- OpenAI GPT-4 for intelligent responses
- PostgreSQL for persistent storage
- Real conversation tracking
- Customer history across sessions
- Ticket management

Run with:
    python demo_api.py

Then open: http://localhost:8000
"""

import json
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded .env file")
except ImportError:
    print("⚠️  python-dotenv not installed. Using system environment variables.")

# FastAPI
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr

# OpenAI Agents SDK
try:
    from agents import Runner, Agent
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️  OpenAI Agents SDK not installed. Using fallback rule-based AI.")
    print("   Install with: pip install openai-agents")

# Database
DATABASE_AVAILABLE = False
DATABASE_ERROR = None
DB_CONNECTION_STATUS = "not_initialized"

try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'production'))
    from production.database.database_operations import (
        init_database,
        close_database,
        get_db_connection,
        get_or_create_customer,
        create_conversation,
        create_message,
        create_ticket,
        get_ticket,
        get_customer_conversations,
        get_conversation_messages,
        get_dashboard_metrics,
        get_daily_sentiment_report,
    )
    print("✅ Database operations module imported")
    DATABASE_AVAILABLE = True  # Set to True if import succeeds
except ImportError as e:
    DATABASE_AVAILABLE = False
    DATABASE_ERROR = str(e)
    print(f"⚠️  Database operations not available: {e}")
    print("   Using in-memory storage (fallback)")

# Kafka
KAFKA_AVAILABLE = False
kafka_producer = None

try:
    from production.workers.kafka_producer import (
        KafkaEventProducer,
        UnifiedTicketEvent,
        EventType,
        ChannelType,
    )
    print("✅ Kafka producer module imported")
    KAFKA_AVAILABLE = True
except ImportError as e:
    KAFKA_AVAILABLE = False
    print(f"⚠️  Kafka producer not available: {e}")
    print("   Events will not be published to Kafka")

# Add src to path for core loop import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'agent'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'production'))

# Import the core loop agent (fallback)
from core_loop_v1_1 import CustomerSupportAgent, CustomerProfile

# Import production tools and prompts if OpenAI is available
openai_agent = None
if OPENAI_AVAILABLE:
    try:
        from production.agent.tools import (
            search_knowledge_base,
            create_ticket as tool_create_ticket,
            get_customer_history,
            escalate_to_human,
            send_response,
        )
        from production.agent.prompts import CUSTOMER_SUCCESS_SYSTEM_PROMPT
        from agents import Agent

        # Create OpenAI agent
        openai_agent = Agent(
            name="NexusFlow Customer Success Digital FTE",
            instructions=CUSTOMER_SUCCESS_SYSTEM_PROMPT,
            tools=[
                search_knowledge_base,
                tool_create_ticket,
                get_customer_history,
                escalate_to_human,
                send_response,
            ],
        )
        print("✅ OpenAI Agent created successfully!")
    except ImportError as e:
        OPENAI_AVAILABLE = False
        print(f"⚠️  Could not import production tools: {e}")
        print("   Using fallback.")
    except Exception as e:
        OPENAI_AVAILABLE = False
        print(f"⚠️  Failed to create OpenAI Agent: {e}")
        print("   Using fallback.")

# =============================================================================
# CONFIGURATION
# =============================================================================

class Config:
    APP_NAME = "NexusFlow Digital FTE - Demo"
    APP_VERSION = "1.0.0"
    DEBUG = True
    HOST = "0.0.0.0"
    PORT = 8000

    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')
    
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/nexusflow')

# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class SupportSubmission(BaseModel):
    """Support form submission model."""
    name: str
    email: str
    subject: str
    description: str
    priority: str = "medium"
    channel: str = "web_form"
    company: Optional[str] = None
    phone: Optional[str] = None
    conversation_id: Optional[str] = None  # For continuing conversations

class SupportResponse(BaseModel):
    """AI-generated support response."""
    success: bool
    response: str
    ticket_id: str
    category: str
    sentiment: str
    urgency: str
    escalation_needed: bool
    escalation_level: str
    metadata: Dict[str, Any]
    ai_source: str  # "openai" or "rule_based"
    conversation_id: Optional[str] = None  # Return conversation ID for continuity

# =============================================================================
# LIFESPAN MANAGEMENT
# =============================================================================

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events (startup and shutdown)."""
    global DATABASE_AVAILABLE, DB_CONNECTION_STATUS
    
    # Startup - Connect to PostgreSQL
    if DATABASE_AVAILABLE:
        try:
            print(f"🔌 Connecting to PostgreSQL...")
            await init_database(Config.DATABASE_URL)
            DB_CONNECTION_STATUS = "connected"
            print("✅ Connected to PostgreSQL successfully")
        except Exception as e:
            DB_CONNECTION_STATUS = "failed"
            print(f"⚠️  PostgreSQL connection failed: {e}")
            print("   Server will start but data will not be persisted")
            # Don't set DATABASE_AVAILABLE to False - let it fail gracefully at runtime

    # Initialize Kafka producer
    if KAFKA_AVAILABLE:
        try:
            print(f"🔌 Connecting to Kafka...")
            global kafka_producer
            kafka_producer = KafkaEventProducer(
                bootstrap_servers="localhost:9092",
                topic="customer-support-tickets",
                max_retries=3,
                retry_delay=1.0
            )
            await kafka_producer.start()
            print("✅ Kafka producer connected")
        except Exception as e:
            print(f"⚠️  Kafka connection failed: {e}")
            print("   Events will not be published to Kafka")

    yield

    # Shutdown
    if DATABASE_AVAILABLE and DB_CONNECTION_STATUS == "connected":
        try:
            await close_database()
            print("✅ PostgreSQL connection closed")
        except Exception as e:
            print(f"Error closing database: {e}")

    # Close Kafka producer
    if KAFKA_AVAILABLE and kafka_producer:
        try:
            await kafka_producer.stop()
            print("✅ Kafka producer stopped")
        except Exception as e:
            print(f"Error closing Kafka: {e}")

# =============================================================================
# CREATE FASTAPI APP
# =============================================================================

app = FastAPI(
    title=Config.APP_NAME,
    description="""
    **24/7 Autonomous AI Customer Support Agent - Demo**

    This demo showcases the NexusFlow Digital FTE with:
    - **OpenAI GPT-4** for intelligent responses (when API key provided)
    - **PostgreSQL** for persistent storage
    - **Rule-based AI** fallback (when no API key)
    - **Sentiment Analysis**: 8 emotion categories
    - **Intent Classification**: 10+ intent patterns
    - **Auto Escalation**: L0-L4 escalation levels

    ## Try It Out

    1. Submit a support request via `/support/submit`
    2. View the AI-generated response
    3. Check if response came from OpenAI or rule-based AI
    """,
    version=Config.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# =============================================================================
# GLOBAL STATE
# =============================================================================

# Initialize agents
rule_based_agent = CustomerSupportAgent()

# Use the openai_agent we created above (if available)
if openai_agent:
    print(f"✅ Using OpenAI Agent with model: {Config.OPENAI_MODEL}")
    openai_runner = openai_agent
else:
    openai_runner = None
    print("⚠️  OpenAI not available, using rule-based AI")

# Store tickets in memory as fallback (only if DB not available)
tickets_db: Dict[str, Dict] = {}
conversations_db: Dict[str, Dict] = {}

# =============================================================================
# AI PROCESSORS
# =============================================================================

async def process_with_openai(
    submission: SupportSubmission,
    conversation_id: Optional[str] = None,
    customer_id: Optional[str] = None
) -> Dict[str, Any]:
    """Process request using OpenAI Agents SDK."""
    try:
        # Build user message with context
        user_message = f"""
Customer: {submission.name} ({submission.email})
Subject: {submission.subject}
Message: {submission.description}
Priority: {submission.priority}
Channel: {submission.channel}

Please provide a helpful customer support response.
"""
        
        print(f"🔍 Running OpenAI Agent with model: {Config.OPENAI_MODEL}")
        
        # Run OpenAI Agent using Runner.run()
        result = await Runner.run(openai_agent, user_message)
        
        print(f"✅ OpenAI Agent completed successfully")
        
        # Extract response
        response_text = result.final_output
        
        print(f"📝 Response generated: {len(response_text)} characters")
        
        # Get tool call information
        tool_calls = getattr(result, 'tool_calls', [])
        used_tools = [call.tool_name for call in tool_calls] if tool_calls else []
        
        return {
            "response": response_text,
            "category": "ai_generated",
            "sentiment": "neutral",
            "urgency": submission.priority,
            "escalation_needed": "escalate" in response_text.lower() or "human" in response_text.lower(),
            "escalation_level": "L1_Tier1" if "escalate" in response_text.lower() else "L0_AI",
            "ai_source": "openai",
            "model": Config.OPENAI_MODEL,
            "tools_used": used_tools,
            "tokens_used": getattr(result, 'usage', {}).get('total_tokens', 0)
        }
    except Exception as e:
        print(f"OpenAI processing failed: {e}")
        # Fallback to rule-based
        return None

def process_with_rule_based(submission: SupportSubmission) -> Dict[str, Any]:
    """Process request using rule-based AI."""
    # Create customer profile
    customer = CustomerProfile(
        name=submission.name,
        email=submission.email,
        plan="Starter"
    )
    
    # Process with rule-based agent
    result = rule_based_agent.process_message(
        message=submission.description,
        channel=submission.channel,
        customer=customer,
        subject=submission.subject
    )
    
    # Add source indicator
    result['metadata']['ai_source'] = 'rule_based'
    
    return result

# =============================================================================
# ROUTES
# =============================================================================

@app.get("/", tags=["Root"])
async def root():
    """API root with information."""
    return {
        "name": Config.APP_NAME,
        "version": Config.APP_VERSION,
        "status": "running",
        "ai_backend": "openai" if openai_runner else "rule_based",
        "database": "postgresql" if DATABASE_AVAILABLE else "in_memory",
        "openai_model": Config.OPENAI_MODEL if openai_runner else None,
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        },
        "endpoints": {
            "health": "/health",
            "submit_support": "/support/submit",
            "dashboard": "/reports/dashboard"
        }
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    health = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": Config.APP_VERSION,
        "ai_backend": "openai" if openai_runner else "rule_based",
        "database": "unknown"
    }
    
    # Check database connection
    if DATABASE_AVAILABLE:
        try:
            async with get_db_connection() as conn:
                await conn.fetchval("SELECT 1")
            health["database"] = "connected"
            health["status"] = "healthy"
        except Exception as e:
            health["database"] = f"error: {str(e)}"
            health["status"] = "degraded"
    else:
        health["database"] = "not_configured"
        health["status"] = "degraded"
    
    return health


@app.get("/test-db", tags=["Health"])
async def test_database():
    """Test database connection and get ticket count."""
    if not DATABASE_AVAILABLE:
        return {
            "status": "error",
            "message": "Database module not available",
            "database": "not_configured"
        }
    
    try:
        async with get_db_connection() as conn:
            # Test connection
            await conn.fetchval("SELECT 1")
            
            # Get real ticket count
            ticket_count = await conn.fetchval("SELECT COUNT(*) FROM tickets")
            
            # Get recent tickets
            recent = await conn.fetch(
                "SELECT id, subject, status, created_at FROM tickets ORDER BY created_at DESC LIMIT 5"
            )
            
            return {
                "status": "success",
                "message": f"Database is LIVE - {ticket_count} tickets found",
                "database": "connected",
                "ticket_count": ticket_count or 0,
                "recent_tickets": [dict(row) for row in recent] if recent else []
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Database connection failed: {str(e)}",
            "database": "error"
        }

@app.get("/support/form", tags=["Support"])
async def get_support_form():
    """Get the simple support form page."""
    from fastapi.responses import FileResponse
    return FileResponse("static/support-form.html")

@app.post("/support/submit", tags=["Support"], response_model=SupportResponse)
async def submit_support(submission: SupportSubmission):
    """
    Submit a support request.
    
    Uses OpenAI GPT-4 if API key is provided, otherwise falls back to rule-based AI.
    Stores all data in PostgreSQL for persistence.
    Publishes events to Kafka for event-driven architecture.
    """
    customer_id = None
    conversation_id = submission.conversation_id
    
    # Try OpenAI first if available
    if openai_runner:
        ai_result = await process_with_openai(submission, conversation_id, customer_id)
        if ai_result:
            # Database operations
            if DATABASE_AVAILABLE:
                try:
                    # Get or create customer
                    customer_id, is_new_customer = await get_or_create_customer(
                        name=submission.name,
                        email=submission.email,
                        company=submission.company,
                        phone=submission.phone
                    )
                    
                    # Create new conversation or use existing
                    if not conversation_id:
                        conversation_id = await create_conversation(
                            customer_id=customer_id,
                            subject=submission.subject,
                            channel=submission.channel,
                            initial_sentiment="neutral"
                        )
                    
                    # Save inbound message
                    await create_message(
                        conversation_id=conversation_id,
                        content=submission.description,
                        direction="inbound",
                        channel=submission.channel,
                        sentiment="neutral"
                    )
                    
                    # Generate ticket ID (format: TKT-YYYYMMDD-XXXXXX where X is alphanumeric)
                    import uuid
                    ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
                    
                    # Save ticket
                    await create_ticket(
                        ticket_id=ticket_id,
                        conversation_id=conversation_id,
                        customer_id=customer_id,
                        subject=submission.subject,
                        description=submission.description,
                        channel=submission.channel,
                        priority=submission.priority
                    )
                    
                    # Save outbound response message
                    await create_message(
                        conversation_id=conversation_id,
                        content=ai_result['response'],
                        direction="outbound",
                        channel=submission.channel,
                        sentiment="neutral",
                        is_ai_generated=True,
                        ai_model=Config.OPENAI_MODEL,
                        ai_tokens_used=ai_result.get('tokens_used', 0)
                    )
                    
                    print(f"✅ Data saved to PostgreSQL: ticket={ticket_id}, conversation={conversation_id}")
                    
                    # Publish to Kafka
                    if KAFKA_AVAILABLE and kafka_producer:
                        try:
                            event = UnifiedTicketEvent.create(
                                event_type=EventType.NEW_MESSAGE,
                                customer_id=customer_id,
                                channel=ChannelType.WEB_FORM,
                                message_content=submission.description,
                                message_id=ticket_id,
                                source_system="demo_api",
                                customer_email=submission.email,
                                message_subject=submission.subject,
                                thread_id=conversation_id,
                                channel_metadata={
                                    "priority": submission.priority,
                                    "name": submission.name
                                }
                            )
                            await kafka_producer.publish_event(event)
                            print(f"📤 Event published to Kafka: {ticket_id}")
                        except Exception as kafka_error:
                            print(f"⚠️  Kafka publish error: {kafka_error}")
                            # Continue anyway - Kafka is optional
                    
                except Exception as e:
                    print(f"⚠️  Database error: {e}")
                    print("   Using in-memory storage (fallback)")
                    # Fallback to in-memory
                    ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d')}-{len(tickets_db) + 1:03d}"
                    tickets_db[ticket_id] = ai_result
            else:
                # In-memory storage
                ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d')}-{len(tickets_db) + 1:03d}"
                tickets_db[ticket_id] = ai_result
            
            return SupportResponse(
                success=True,
                response=ai_result['response'],
                ticket_id=ticket_id,
                category=ai_result.get('category', 'ai_generated'),
                sentiment=ai_result.get('sentiment', 'neutral'),
                urgency=ai_result.get('urgency', submission.priority),
                escalation_needed=ai_result.get('escalation_needed', False),
                escalation_level=ai_result.get('escalation_level', 'L0_AI'),
                metadata={
                    "ai_source": "openai",
                    "model": Config.OPENAI_MODEL,
                    "tools_used": ai_result.get('tools_used', []),
                    "tokens_used": ai_result.get('tokens_used', 0)
                },
                ai_source="openai",
                conversation_id=conversation_id
            )
    
    # Fallback to rule-based AI
    result = process_with_rule_based(submission)
    
    # Store ticket
    ticket = result.get('ticket', {})
    ticket_id = ticket.get('ticket_id', f'DEMO-{len(tickets_db) + 1}')
    tickets_db[ticket_id] = result
    
    return SupportResponse(
        success=result.get('success', True),
        response=result.get('response', ''),
        ticket_id=ticket_id,
        category=result['metadata'].get('category', 'general'),
        sentiment=result['metadata'].get('sentiment', 'neutral'),
        urgency=result['metadata'].get('urgency', 'medium'),
        escalation_needed=result['metadata'].get('escalation_needed', False),
        escalation_level=result['metadata'].get('escalation_level', 'L0_AI'),
        metadata=result.get('metadata', {}),
        ai_source="rule_based",
        conversation_id=conversation_id
    )

@app.get("/reports/dashboard", tags=["Reports"])
async def get_dashboard():
    """Get real-time dashboard metrics."""
    if DATABASE_AVAILABLE:
        try:
            # Get real metrics from database
            metrics = await get_dashboard_metrics()
            
            return {
                "timestamp": datetime.now().isoformat(),
                "overview": {
                    "total_tickets": metrics['total_tickets'],
                    "resolved_by_ai": metrics['ai_resolved_count'],
                    "escalated_to_human": metrics['tickets_by_status'].get('escalated', 0),
                    "ai_resolution_rate": f"{metrics['ai_resolution_rate']}%"
                },
                "sentiment_distribution": metrics['sentiment_distribution'],
                "category_distribution": metrics['tickets_by_status'],
                "channel_distribution": metrics['tickets_by_channel'],
                "priority_distribution": metrics['tickets_by_priority'],
                "recent_tickets": metrics['recent_tickets'][:5]
            }
        except Exception as e:
            print(f"Dashboard DB error: {e}")
            # Fallback to in-memory
    
    # In-memory fallback
    total_tickets = len(tickets_db)
    escalated = sum(1 for t in tickets_db.values() if t.get('metadata', {}).get('escalation_needed', False))
    
    # Count by sentiment
    sentiment_counts = {}
    for t in tickets_db.values():
        sentiment = t.get('metadata', {}).get('sentiment', 'unknown')
        sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
    
    # Count by category
    category_counts = {}
    for t in tickets_db.values():
        category = t.get('metadata', {}).get('category', 'unknown')
        category_counts[category] = category_counts.get(category, 0) + 1
    
    # Count by AI source
    ai_source_counts = {"openai": 0, "rule_based": 0}
    for t in tickets_db.values():
        source = t.get('metadata', {}).get('ai_source', 'rule_based')
        ai_source_counts[source] = ai_source_counts.get(source, 0) + 1
    
    return {
        "timestamp": datetime.now().isoformat(),
        "overview": {
            "total_tickets": total_tickets,
            "resolved_by_ai": total_tickets - escalated,
            "escalated_to_human": escalated,
            "ai_resolution_rate": f"{((total_tickets - escalated) / max(total_tickets, 1) * 100):.1f}%"
        },
        "sentiment_distribution": sentiment_counts,
        "category_distribution": category_counts,
        "ai_source_distribution": ai_source_counts,
        "recent_tickets": list(tickets_db.keys())[-5:]
    }

@app.get("/reports/daily-sentiment", tags=["Reports"])
async def get_daily_sentiment(days: int = 7):
    """Get daily sentiment report."""
    if DATABASE_AVAILABLE:
        try:
            report = await get_daily_sentiment_report(days)
            return {
                "timestamp": datetime.now().isoformat(),
                "days": days,
                "report": report
            }
        except Exception as e:
            print(f"Daily sentiment DB error: {e}")
    
    # Fallback mock data
    return {
        "timestamp": datetime.now().isoformat(),
        "days": days,
        "report": [
            {"date": datetime.now().strftime('%Y-%m-%d'), "sentiments": {"neutral": 5, "positive": 3}}
        ]
    }

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 80)
    print("NEXUSFLOW DIGITAL FTE - DEMO API (PostgreSQL + OpenAI)")
    print("=" * 80)
    print(f"\nStarting server on http://{Config.HOST}:{Config.PORT}")
    print(f"API Documentation: http://{Config.HOST}:{Config.PORT}/docs")
    print(f"AI Backend: {'OpenAI GPT-4' if openai_runner else 'Rule-Based (Fallback)'}")
    print(f"Database: {'PostgreSQL' if DATABASE_AVAILABLE else 'In-Memory (Fallback)'}")
    if openai_runner:
        print(f"OpenAI Model: {Config.OPENAI_MODEL}")
    if DATABASE_AVAILABLE:
        print(f"Database URL: {Config.DATABASE_URL}")
    else:
        print("\nTo use PostgreSQL:")
        print("  1. Install PostgreSQL")
        print("  2. Create database: CREATE DATABASE nexusflow;")
        print("  3. Set DATABASE_URL in .env")
        print("  4. Restart the server")
    
    print("\nTo use OpenAI:")
    print("  1. Get API key from https://platform.openai.com")
    print("  2. Set environment variable: OPENAI_API_KEY=sk-...")
    print("  3. Restart the server")
    print("\nPress Ctrl+C to stop\n")
    print("=" * 80)
    
    uvicorn.run(
        "demo_api:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG
    )
