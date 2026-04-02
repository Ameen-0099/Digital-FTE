"""
NexusFlow Customer Success Digital FTE - API Package
=====================================================

This package contains the FastAPI application that serves as the central
entry point for all customer support channels.

The API:
- Receives messages from Gmail, WhatsApp, and Web Form
- Normalizes payloads into unified events
- Publishes to Kafka for async processing
- Returns immediate 202 Accepted responses

Modules:
- main: FastAPI application with all routes and middleware
"""

from .main import app, create_app, Config, AppState

__all__ = [
    "app",
    "create_app",
    "Config",
    "AppState"
]
