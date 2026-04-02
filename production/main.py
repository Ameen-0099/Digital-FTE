"""
NexusFlow Customer Success Digital FTE - Main Entry Point
==========================================================
Exercise 2.6: Production Entry Point

Unified entry point that starts both the FastAPI API server
and the background workers (message processor + metrics collector).

Usage:
    python -m production.main

Or with uvicorn for production:
    uvicorn production.main:app --host 0.0.0.0 --port 8000 --workers 4

Author: Digital FTE Team
Version: 1.0.0 (Production)
"""

import asyncio
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager
from typing import Optional

# FastAPI
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Local imports
from workers.message_processor import DatabasePool, Config as WorkerConfig
from workers.metrics_collector import MetricsCollector
from api.main import router as api_router
from api.reports import router as reports_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# GLOBAL STATE
# =============================================================================

class ApplicationState:
    """Global application state."""
    metrics_collector: Optional[MetricsCollector] = None
    shutdown_event: Optional[asyncio.Event] = None


# =============================================================================
# LIFESPAN MANAGER
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown of all components:
    - Database connection pool
    - Kafka producer
    - Metrics collector (background task)
    """
    logger.info("=" * 80)
    logger.info("NEXUSFLOW DIGITAL FTE - STARTING")
    logger.info("=" * 80)
    
    try:
        # Initialize database
        logger.info("Initializing database connection pool...")
        await DatabasePool.create_pool(WorkerConfig.DATABASE_URL)
        logger.info("✅ Database pool initialized")
        
        # Initialize metrics collector
        logger.info("Initializing metrics collector...")
        ApplicationState.metrics_collector = MetricsCollector()
        await ApplicationState.metrics_collector.initialize()
        await ApplicationState.metrics_collector.start()
        logger.info("✅ Metrics collector started")
        
        # Create shutdown event
        ApplicationState.shutdown_event = asyncio.Event()
        
        logger.info("=" * 80)
        logger.info("✅ ALL COMPONENTS INITIALIZED")
        logger.info(f"API listening on {WorkerConfig.HOST}:{WorkerConfig.PORT}")
        logger.info("=" * 80)
        
        yield  # Application runs here
        
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise
    
    finally:
        # SHUTDOWN
        logger.info("Shutting down application...")
        
        if ApplicationState.metrics_collector:
            await ApplicationState.metrics_collector.stop()
            logger.info("✅ Metrics collector stopped")
        
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
        title="NexusFlow Customer Success Digital FTE",
        description="""
        **24/7 Autonomous AI Customer Support Agent**
        
        The NexusFlow Digital FTE is a production-grade AI employee that handles
        customer support across multiple channels (Email, WhatsApp, Web Form) with:
        
        - **Automatic ticket creation** and customer identification
        - **Intelligent responses** powered by OpenAI GPT-4
        - **Cross-channel memory** for seamless conversations
        - **Automatic escalation** to human agents when needed
        - **Daily sentiment reports** and performance metrics
        
        ## Architecture
        
        ```
        Channels → FastAPI → Kafka → Agent Worker → DB + Reply
        ```
        
        ## Key Features
        
        - **Multi-channel**: Email (Gmail), WhatsApp (Twilio), Web Form
        - **AI-powered**: OpenAI Agents SDK with custom tools
        - **Persistent memory**: PostgreSQL with pgvector for semantic search
        - **Event-driven**: Kafka for reliable message streaming
        - **Production-ready**: Kubernetes deployment with auto-scaling
        """,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(api_router)  # Main API routes
    app.include_router(reports_router)  # Reports routes
    
    # Root endpoint
    @app.get("/", tags=["Root"])
    async def root():
        """API root with information and links."""
        return {
            "name": "NexusFlow Customer Success Digital FTE",
            "version": "1.0.0",
            "status": "running",
            "documentation": {
                "swagger": "/docs",
                "redoc": "/redoc",
                "openapi": "/openapi.json"
            },
            "endpoints": {
                "health": "/health",
                "metrics": "/metrics",
                "reports": {
                    "daily_sentiment": "/reports/daily-sentiment",
                    "dashboard": "/reports/dashboard",
                    "trends": "/reports/trends"
                },
                "webhooks": {
                    "gmail": "/webhook/gmail",
                    "whatsapp": "/webhook/whatsapp"
                },
                "support": "/support/submit"
            }
        }
    
    return app


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

app = create_app()


def main():
    """
    Main entry point for running the Digital FTE.
    
    Starts both the FastAPI server and background workers.
    """
    import uvicorn
    
    logger.info("Starting NexusFlow Digital FTE...")
    
    # Run with uvicorn
    uvicorn.run(
        "production.main:app",
        host=os.getenv('API_HOST', '0.0.0.0'),
        port=int(os.getenv('API_PORT', '8000')),
        reload=os.getenv('DEBUG', 'false').lower() == 'true',
        workers=int(os.getenv('API_WORKERS', '4')),
        log_level=os.getenv('LOG_LEVEL', 'info').lower()
    )


if __name__ == "__main__":
    main()
