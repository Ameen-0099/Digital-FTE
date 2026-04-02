"""
NexusFlow Customer Success Digital FTE - FastAPI API Layer
===========================================================
Exercise 2.4: Production API - Central Entry Point for All Channels

This is the central entry point for all customer support channels. It receives
incoming messages from Gmail, WhatsApp, and Web Form, normalizes them into
unified events, publishes to Kafka, and returns immediate acknowledgments.

The API Layer enables the 24/7 autonomous Digital FTE by:
1. Accepting messages from all channels asynchronously
2. Publishing to Kafka for reliable event streaming
3. Returning immediate 202 Accepted (no timeout issues)
4. The Message Processor then handles the actual AI processing

Author: Digital FTE Team
Version: 1.0.0 (Production)
"""

import asyncio
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

# FastAPI
from fastapi import FastAPI, Request, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.logger import logger as fastapi_logger

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Local imports
from workers.kafka_producer import (
    KafkaEventProducer,
    UnifiedTicketEvent,
    EventType,
    ChannelType
)

from channels.gmail_handler import GmailWebhookHandler, GmailClient, create_gmail_webhook_app
from channels.whatsapp_handler import WhatsAppWebhookHandler, TwilioWhatsAppClient, create_whatsapp_webhook_app
from channels.web_form_handler import router as web_form_router, SupportFormSubmission, WebFormHandler

# Database pool
from workers.message_processor import DatabasePool

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
    
    # Application
    APP_NAME = "NexusFlow Digital FTE API"
    APP_VERSION = "1.0.0"
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    
    # Server
    HOST = os.getenv('API_HOST', '0.0.0.0')
    PORT = int(os.getenv('API_PORT', '8000'))
    
    # Kafka
    KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'customer-support-tickets')
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/nexusflow')
    
    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
    
    # Gmail
    GMAIL_SERVICE_ACCOUNT = os.getenv('GMAIL_SERVICE_ACCOUNT_FILE', '')
    GMAIL_DELEGATED_EMAIL = os.getenv('GMAIL_DELEGATED_EMAIL', '')
    GMAIL_PUBSUB_VALIDATION_TOKEN = os.getenv('GMAIL_PUBSUB_VALIDATION_TOKEN', '')
    
    # Twilio
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
    TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER', '')
    
    # Metrics
    METRICS_ENABLED = os.getenv('METRICS_ENABLED', 'true').lower() == 'true'


# =============================================================================
# GLOBAL STATE
# =============================================================================

class AppState:
    """Global application state management."""
    
    kafka_producer: Optional[KafkaEventProducer] = None
    gmail_client: Optional[GmailClient] = None
    twilio_client: Optional[TwilioWhatsAppClient] = None
    web_form_handler: Optional[WebFormHandler] = None
    
    # Metrics counters
    metrics = {
        'total_requests': 0,
        'total_messages_received': 0,
        'messages_by_channel': {
            'email': 0,
            'whatsapp': 0,
            'web_form': 0
        },
        'errors': 0,
        'start_time': None
    }
    
    @classmethod
    def increment_metric(cls, metric: str, channel: Optional[str] = None):
        """Increment a metric counter."""
        if metric in cls.metrics:
            cls.metrics[metric] += 1
        elif channel and metric == 'channel_message':
            if channel in cls.metrics['messages_by_channel']:
                cls.metrics['messages_by_channel'][channel] += 1
    
    @classmethod
    def get_uptime(cls) -> float:
        """Get application uptime in seconds."""
        if cls.metrics['start_time']:
            return time.time() - cls.metrics['start_time']
        return 0.0


# =============================================================================
# LIFESPAN MANAGEMENT
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events for database, Kafka, and channel clients.
    """
    # STARTUP
    logger.info("=" * 80)
    logger.info(f"Starting {Config.APP_NAME} v{Config.APP_VERSION}")
    logger.info("=" * 80)

    try:
        # Initialize database pool
        logger.info("Initializing database connection pool...")
        await DatabasePool.create_pool(Config.DATABASE_URL)
        logger.info("✅ Database pool initialized")

        # Initialize Kafka producer with retry
        logger.info("Initializing Kafka producer...")
        AppState.kafka_producer = KafkaEventProducer(
            bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS,
            topic=Config.KAFKA_TOPIC,
            max_retries=5,
            retry_delay=2.0
        )
        
        # Retry Kafka connection with backoff
        max_kafka_retries = 5
        for attempt in range(max_kafka_retries):
            try:
                await AppState.kafka_producer.start()
                logger.info("✅ Kafka producer initialized")
                break
            except Exception as e:
                if attempt < max_kafka_retries - 1:
                    logger.warning(f"Kafka connection failed (attempt {attempt + 1}/{max_kafka_retries}): {e}")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Failed to connect to Kafka after {max_kafka_retries} attempts: {e}")
                    raise
        
        # Initialize Gmail client (if configured)
        if Config.GMAIL_SERVICE_ACCOUNT and Config.GMAIL_DELEGATED_EMAIL:
            logger.info("Initializing Gmail client...")
            AppState.gmail_client = GmailClient(
                service_account_file=Config.GMAIL_SERVICE_ACCOUNT,
                delegated_email=Config.GMAIL_DELEGATED_EMAIL,
                project_id=os.getenv('GCP_PROJECT_ID', ''),
                topic_name=os.getenv('GMAIL_PUBSUB_TOPIC', '')
            )
            logger.info("✅ Gmail client initialized")
        else:
            logger.info("⚠️  Gmail not configured (skipping)")
        
        # Initialize Twilio client (if configured)
        if Config.TWILIO_ACCOUNT_SID and Config.TWILIO_AUTH_TOKEN:
            logger.info("Initializing Twilio WhatsApp client...")
            AppState.twilio_client = TwilioWhatsAppClient(
                account_sid=Config.TWILIO_ACCOUNT_SID,
                auth_token=Config.TWILIO_AUTH_TOKEN,
                whatsapp_number=Config.TWILIO_WHATSAPP_NUMBER
            )
            logger.info("✅ Twilio WhatsApp client initialized")
        else:
            logger.info("⚠️  Twilio not configured (skipping)")
        
        # Initialize web form handler
        logger.info("Initializing web form handler...")
        AppState.web_form_handler = WebFormHandler()
        logger.info("✅ Web form handler initialized")
        
        # Set start time for metrics
        AppState.metrics['start_time'] = time.time()
        
        logger.info("=" * 80)
        logger.info("✅ All components initialized successfully")
        logger.info(f"API listening on {Config.HOST}:{Config.PORT}")
        logger.info("=" * 80)
        
        yield  # Application runs here
        
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise
    
    finally:
        # SHUTDOWN
        logger.info("Shutting down application...")
        
        if AppState.kafka_producer:
            await AppState.kafka_producer.stop()
            logger.info("✅ Kafka producer stopped")
        
        await DatabasePool.close_pool()
        logger.info("✅ Database pool closed")
        
        logger.info("✅ Shutdown complete")


# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title=Config.APP_NAME,
        description="""
        **NexusFlow Customer Success Digital FTE API**
        
        This API serves as the central entry point for all customer support channels:
        - **Gmail/Email**: Webhook for incoming emails via Google Pub/Sub
        - **WhatsApp**: Webhook for incoming messages via Twilio
        - **Web Form**: REST endpoint for support form submissions
        
        All incoming messages are normalized and published to Kafka for processing
        by the autonomous Digital FTE agent worker.
        
        ## Architecture
        
        ```
        Channels → FastAPI API → Kafka → Agent Worker → DB + Reply
        ```
        
        ## Response Times
        
        - API acknowledges all messages within 200ms (202 Accepted)
        - Digital FTE agent processes messages asynchronously
        - Typical response time: 1-2 minutes depending on complexity
        """,
        version=Config.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=Config.CORS_ORIGINS if Config.CORS_ORIGINS != ['*'] else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all incoming requests for audit trail."""
        start_time = time.time()
        
        response = await call_next(request)
        
        duration = time.time() - start_time
        AppState.increment_metric('total_requests')
        
        logger.info(
            f"{request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Duration: {duration:.3f}s"
        )
        
        return response
    
    # Register routes
    register_routes(app)
    
    return app


# =============================================================================
# ROUTES
# =============================================================================

def register_routes(app: FastAPI):
    """Register all API routes."""
    
    # Include web form router
    app.include_router(web_form_router, prefix="/support", tags=["Web Form"])
    
    # Gmail webhook
    @app.post(
        "/webhook/gmail",
        tags=["Gmail"],
        summary="Gmail Webhook",
        description="Receive incoming email notifications from Google Pub/Sub",
        response_model=Dict[str, str],
        responses={
            200: {"description": "Webhook processed successfully"},
            400: {"description": "Invalid webhook payload"},
            500: {"description": "Internal server error"}
        }
    )
    async def gmail_webhook(request: Request):
        """
        Handle Gmail webhook notifications from Google Cloud Pub/Sub.
        
        This endpoint receives push notifications when new emails arrive.
        It validates the Pub/Sub message and publishes to Kafka for processing.
        """
        try:
            # Parse request
            data = await request.json()
            
            # Validate Pub/Sub message
            if not _validate_gmail_pubsub(data):
                logger.warning("Invalid Gmail Pub/Sub message")
                raise HTTPException(status_code=400, detail="Invalid Pub/Sub message")
            
            # Extract message data
            message_data = data.get('message', {})
            attributes = message_data.get('attributes', {})
            message_id = attributes.get('message_id')
            
            if not message_id:
                raise HTTPException(status_code=400, detail="Missing message_id")
            
            # Publish to Kafka (actual email fetching happens in worker)
            await _publish_gmail_event(
                message_id=message_id,
                attributes=attributes
            )
            
            AppState.increment_metric('total_messages_received')
            AppState.increment_metric('channel_message', 'email')
            
            logger.info(f"Gmail webhook processed: {message_id}")
            
            # Return 202 Accepted (async processing)
            return {
                "status": "accepted",
                "message_id": message_id,
                "message": "Email queued for processing"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Gmail webhook error: {e}", exc_info=True)
            AppState.increment_metric('errors')
            raise HTTPException(status_code=500, detail=str(e))
    
    # WhatsApp webhook
    @app.post(
        "/webhook/whatsapp",
        tags=["WhatsApp"],
        summary="WhatsApp Webhook",
        description="Receive incoming WhatsApp messages from Twilio",
        response_model=Dict[str, str],
        responses={
            200: {"description": "Webhook processed successfully"},
            400: {"description": "Invalid webhook payload"},
            403: {"description": "Invalid Twilio signature"},
            500: {"description": "Internal server error"}
        }
    )
    async def whatsapp_webhook(request: Request):
        """
        Handle WhatsApp webhook from Twilio.
        
        This endpoint receives incoming WhatsApp messages and publishes
        them to Kafka for processing by the Digital FTE agent.
        """
        try:
            # Get signature for validation
            signature = request.headers.get('X-Twilio-Signature', '')
            
            # Read body
            body = await request.read()
            
            # Validate signature in production
            if os.getenv('ENVIRONMENT', 'development') == 'production':
                if not _validate_twilio_signature(str(request.url), body, signature):
                    logger.warning("Invalid Twilio signature")
                    raise HTTPException(status_code=403, detail="Invalid signature")
            
            # Parse form data
            params = await request.form()
            
            # Extract message data
            from_number = params.get('From', '')
            message_body = params.get('Body', '')
            message_sid = params.get('MessageSid', '')
            media_url = params.get('MediaUrl0')
            
            if not from_number or not message_sid:
                raise HTTPException(status_code=400, detail="Missing required fields")
            
            # Publish to Kafka
            await _publish_whatsapp_event(
                from_number=from_number,
                message_body=message_body,
                message_sid=message_sid,
                media_url=media_url,
                media_type=params.get('MediaType0')
            )
            
            AppState.increment_metric('total_messages_received')
            AppState.increment_metric('channel_message', 'whatsapp')
            
            logger.info(f"WhatsApp webhook processed: {message_sid}")
            
            # Return 202 Accepted (async processing)
            return {
                "status": "accepted",
                "message_sid": message_sid,
                "message": "Message queued for processing"
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"WhatsApp webhook error: {e}", exc_info=True)
            AppState.increment_metric('errors')
            raise HTTPException(status_code=500, detail=str(e))
    
    # Health check
    @app.get(
        "/health",
        tags=["Health"],
        summary="Health Check",
        description="Check API health status for Kubernetes probes",
        response_model=Dict[str, Any]
    )
    async def health_check():
        """
        Health check endpoint for Kubernetes liveness/readiness probes.
        
        Returns healthy status if all core components are connected.
        """
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": Config.APP_VERSION,
            "uptime_seconds": round(AppState.get_uptime(), 2),
            "components": {
                "database": "unknown",
                "kafka": "unknown"
            }
        }
        
        # Check database
        try:
            pool = await DatabasePool.get_pool()
            async with pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            health_status["components"]["database"] = "connected"
        except Exception as e:
            health_status["components"]["database"] = f"error: {str(e)}"
            health_status["status"] = "degraded"
        
        # Check Kafka
        try:
            if AppState.kafka_producer and AppState.kafka_producer._is_running:
                health_status["components"]["kafka"] = "connected"
            else:
                health_status["components"]["kafka"] = "disconnected"
                health_status["status"] = "degraded"
        except Exception as e:
            health_status["components"]["kafka"] = f"error: {str(e)}"
            health_status["status"] = "degraded"
        
        status_code = 200 if health_status["status"] == "healthy" else 503
        return JSONResponse(status_code=status_code, content=health_status)
    
    # Metrics endpoint
    @app.get(
        "/metrics",
        tags=["Metrics"],
        summary="Agent Metrics",
        description="Get current agent metrics and statistics",
        response_model=Dict[str, Any]
    )
    async def get_metrics():
        """
        Get current agent metrics.
        
        Returns statistics about message processing, channel distribution,
        and system performance.
        """
        if not Config.METRICS_ENABLED:
            raise HTTPException(status_code=404, detail="Metrics disabled")
        
        # Calculate rates
        uptime = AppState.get_uptime()
        messages_per_minute = (
            AppState.metrics['total_messages_received'] / (uptime / 60)
            if uptime > 0 else 0
        )
        
        return {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": round(uptime, 2),
            "total_requests": AppState.metrics['total_requests'],
            "total_messages_received": AppState.metrics['total_messages_received'],
            "messages_per_minute": round(messages_per_minute, 2),
            "messages_by_channel": AppState.metrics['messages_by_channel'],
            "errors": AppState.metrics['errors'],
            "version": Config.APP_VERSION
        }
    
    # Root endpoint
    @app.get(
        "/",
        tags=["Root"],
        summary="API Root",
        description="API information and documentation links",
        response_model=Dict[str, Any]
    )
    async def root():
        """API root with documentation links."""
        return {
            "name": Config.APP_NAME,
            "version": Config.APP_VERSION,
            "documentation": {
                "swagger": "/docs",
                "redoc": "/redoc",
                "openapi": "/openapi.json"
            },
            "endpoints": {
                "health": "/health",
                "metrics": "/metrics",
                "webhooks": {
                    "gmail": "/webhook/gmail",
                    "whatsapp": "/webhook/whatsapp"
                },
                "support": "/support/submit"
            }
        }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _validate_gmail_pubsub(data: Dict[str, Any]) -> bool:
    """
    Validate Gmail Pub/Sub message format.
    
    Args:
        data: Message data from request
        
    Returns:
        True if valid
    """
    if 'message' not in data:
        return False
    
    message = data['message']
    if 'data' not in message or 'attributes' not in message:
        return False
    
    # Validate token if configured
    token = message.get('attributes', {}).get('validationToken', '')
    if Config.GMAIL_PUBSUB_VALIDATION_TOKEN and token != Config.GMAIL_PUBSUB_VALIDATION_TOKEN:
        return False
    
    return True


async def _publish_gmail_event(message_id: str, attributes: Dict[str, Any]):
    """
    Publish Gmail event to Kafka.
    
    Args:
        message_id: Gmail message ID
        attributes: Pub/Sub attributes
    """
    if not AppState.kafka_producer:
        logger.error("Kafka producer not initialized")
        return
    
    event = UnifiedTicketEvent.create(
        event_type=EventType.NEW_MESSAGE,
        customer_id=attributes.get('email', 'unknown'),
        channel=ChannelType.EMAIL,
        message_content="",  # Will be fetched by worker
        message_id=message_id,
        source_system="gmail",
        customer_email=attributes.get('email'),
        message_subject=attributes.get('subject'),
        thread_id=attributes.get('thread_id'),
        channel_metadata={
            "provider": "gmail",
            "pubsub_attributes": attributes
        }
    )
    
    await AppState.kafka_producer.publish_event(event)


def _validate_twilio_signature(url: str, body: bytes, signature: str) -> bool:
    """
    Validate Twilio webhook signature.
    
    Args:
        url: Full webhook URL
        body: Request body
        signature: X-Twilio-Signature header
        
    Returns:
        True if signature is valid
    """
    try:
        from twilio.request_validator import RequestValidator
        validator = RequestValidator(Config.TWILIO_AUTH_TOKEN)
        
        # Parse body as form data
        params = {}
        body_str = body.decode('utf-8')
        for pair in body_str.split('&'):
            if '=' in pair:
                key, value = pair.split('=', 1)
                params[key] = value
        
        return validator.validate(url, params, signature)
        
    except Exception as e:
        logger.error(f"Signature validation error: {e}")
        return False


async def _publish_whatsapp_event(
    from_number: str,
    message_body: str,
    message_sid: str,
    media_url: Optional[str] = None,
    media_type: Optional[str] = None
):
    """
    Publish WhatsApp event to Kafka.
    
    Args:
        from_number: Sender phone number
        message_body: Message text
        message_sid: Twilio message SID
        media_url: Optional media URL
        media_type: Optional media type
    """
    if not AppState.kafka_producer:
        logger.error("Kafka producer not initialized")
        return
    
    event = UnifiedTicketEvent.create(
        event_type=EventType.NEW_MESSAGE,
        customer_id=from_number,
        channel=ChannelType.WHATSAPP,
        message_content=message_body,
        message_id=message_sid,
        source_system="whatsapp",
        customer_phone=from_number,
        channel_metadata={
            "provider": "twilio",
            "media_url": media_url,
            "media_type": media_type
        }
    )
    
    await AppState.kafka_producer.publish_event(event)


# =============================================================================
# CREATE APPLICATION INSTANCE
# =============================================================================

app = create_app()


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    """
    Run the FastAPI application.
    
    For production, use:
        uvicorn production.api.main:app --host 0.0.0.0 --port 8000 --workers 4
    
    For development with auto-reload:
        uvicorn production.api.main:app --reload
    """
    import uvicorn
    
    logger.info(f"Starting {Config.APP_NAME} on {Config.HOST}:{Config.PORT}")
    
    uvicorn.run(
        "production.api.main:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG,
        workers=1 if Config.DEBUG else 4,
        log_level="info"
    )
