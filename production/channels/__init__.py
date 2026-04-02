"""
NexusFlow Customer Success Digital FTE - Channels Package
==========================================================

This package contains channel integration handlers for multi-channel
customer support.

Modules:
- gmail_handler: Gmail API integration with Pub/Sub webhooks
- whatsapp_handler: Twilio WhatsApp Business API integration
- web_form_handler: FastAPI web form with embeddable UI

All handlers:
- Return standardized message format
- Integrate with PostgreSQL database
- Are fully async and production-ready
- Include proper error handling and logging
"""

from .gmail_handler import (
    GmailClient,
    GmailWebhookHandler,
    EmailResponseSender,
    create_gmail_webhook_app,
    EmailMessage,
    ProcessedEmail
)

from .whatsapp_handler import (
    TwilioWhatsAppClient,
    WhatsAppWebhookHandler,
    WhatsAppResponseSender,
    create_whatsapp_webhook_app,
    WhatsAppMessage,
    ProcessedWhatsAppMessage
)

from .web_form_handler import (
    WebFormHandler,
    SupportFormSubmission,
    SupportFormResponse,
    create_web_form_app,
    ProcessedWebForm,
    router
)

__all__ = [
    # Gmail
    "GmailClient",
    "GmailWebhookHandler",
    "EmailResponseSender",
    "create_gmail_webhook_app",
    "EmailMessage",
    "ProcessedEmail",
    
    # WhatsApp
    "TwilioWhatsAppClient",
    "WhatsAppWebhookHandler",
    "WhatsAppResponseSender",
    "create_whatsapp_webhook_app",
    "WhatsAppMessage",
    "ProcessedWhatsAppMessage",
    
    # Web Form
    "WebFormHandler",
    "SupportFormSubmission",
    "SupportFormResponse",
    "create_web_form_app",
    "ProcessWebForm",
    "router"
]
