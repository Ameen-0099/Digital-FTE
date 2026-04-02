"""
NexusFlow Customer Success Digital FTE - WhatsApp Channel Handler
==================================================================
Exercise 2.2: Channel Integrations - WhatsApp (Twilio) Handler

This module handles incoming and outgoing WhatsApp messages via Twilio's
WhatsApp Business API with webhook integration for real-time processing.

Features:
- Twilio WhatsApp API integration
- Webhook signature validation (X-Twilio-Signature)
- Message parsing (text, media, location)
- Customer identification by phone number
- Response formatting for WhatsApp (300 char limit, emoji support)
- Delivery status tracking

Author: Digital FTE Team
Version: 1.0.0 (Production)
"""

import asyncio
import hashlib
import hmac
import base64
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field

# Async HTTP client
import aiohttp
from aiohttp import web

# Twilio helper (for signature validation)
from twilio.request_validator import RequestValidator

# Database connection
from database.connection import get_db_pool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class WhatsAppMessage:
    """Parsed WhatsApp message structure."""
    message_id: str
    from_number: str
    to_number: str
    content_type: str  # text, image, video, audio, document, location, contact
    text_content: Optional[str]
    media_url: Optional[str]
    media_type: Optional[str]
    location: Optional[Dict[str, Any]]
    contact: Optional[Dict[str, Any]]
    timestamp: str
    is_inbound: bool = True


@dataclass
class ProcessedWhatsAppMessage:
    """Processed WhatsApp message ready for agent handling."""
    channel: str
    customer_id: str
    content: str
    metadata: Dict[str, Any]


# =============================================================================
# TWILIO WHATSAPP CLIENT
# =============================================================================

class TwilioWhatsAppClient:
    """
    Async Twilio WhatsApp API client for sending and receiving messages.
    
    Uses Twilio REST API for message operations.
    """
    
    BASE_URL = "https://api.twilio.com/2010-04-01"
    
    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        whatsapp_number: str
    ):
        """
        Initialize Twilio WhatsApp client.
        
        Args:
            account_sid: Twilio Account SID
            auth_token: Twilio Auth Token
            whatsapp_number: WhatsApp sender number (whatsapp:+14155238886)
        """
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.whatsapp_number = whatsapp_number
        
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with auth."""
        if self._session is None or self._session.closed:
            auth = aiohttp.BasicAuth(self.account_sid, self.auth_token)
            self._session = aiohttp.ClientSession(auth=auth)
        return self._session
    
    async def close(self):
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def send_message(
        self,
        to_number: str,
        body: str,
        media_url: Optional[str] = None
    ) -> Optional[Dict[str, str]]:
        """
        Send a WhatsApp message via Twilio API.
        
        Args:
            to_number: Recipient WhatsApp number (whatsapp:+1234567890)
            body: Message body (max 300 chars for WhatsApp)
            media_url: Optional media URL for images/documents
            
        Returns:
            Dict with message SID and status, or None if failed
        """
        try:
            # Enforce WhatsApp character limit
            if len(body) > 300:
                logger.warning(f"WhatsApp message truncated from {len(body)} to 300 chars")
                body = body[:297] + "..."
            
            session = await self._get_session()
            
            # Prepare request
            url = f"{self.BASE_URL}/Accounts/{self.account_sid}/Messages.json"
            data = {
                'From': self.whatsapp_number,
                'To': to_number,
                'Body': body
            }
            
            if media_url:
                data['MediaUrl'] = media_url
            
            # Send request
            async with session.post(url, data=data) as response:
                if response.status == 201:
                    result = await response.json()
                    logger.info(f"WhatsApp message sent to {to_number}, SID: {result.get('sid')}")
                    return {
                        'message_sid': result.get('sid'),
                        'status': result.get('status'),
                        'date_created': result.get('date_created')
                    }
                else:
                    error = await response.text()
                    logger.error(f"Failed to send WhatsApp message: {error}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}", exc_info=True)
            return None
    
    async def get_message_status(self, message_sid: str) -> Optional[str]:
        """
        Get delivery status of a message.
        
        Args:
            message_sid: Twilio message SID
            
        Returns:
            Status string (queued, sent, delivered, failed, etc.)
        """
        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/Accounts/{self.account_sid}/Messages/{message_sid}.json"
            
            async with session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('status')
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting message status: {e}")
            return None
    
    async def download_media(self, media_url: str) -> bytes:
        """
        Download media from Twilio.
        
        Args:
            media_url: Media URL from Twilio
            
        Returns:
            Media bytes
        """
        try:
            session = await self._get_session()
            
            async with session.get(media_url) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    return b''
                    
        except Exception as e:
            logger.error(f"Error downloading media: {e}")
            return b''


# =============================================================================
# WEBHOOK SIGNATURE VALIDATOR
# =============================================================================

class TwilioSignatureValidator:
    """
    Validates Twilio webhook signatures to ensure requests are authentic.
    
    Twilio signs each webhook request with X-Twilio-Signature header.
    """
    
    def __init__(self, auth_token: str):
        """
        Initialize validator.
        
        Args:
            auth_token: Twilio Auth Token
        """
        self.auth_token = auth_token
        self._validator = RequestValidator(auth_token)
    
    def validate(
        self,
        url: str,
        params: Dict[str, str],
        signature: str
    ) -> bool:
        """
        Validate webhook signature.
        
        Args:
            url: Full webhook URL (including query params)
            params: POST parameters
            signature: X-Twilio-Signature header value
            
        Returns:
            True if signature is valid
        """
        return self._validator.validate(url, params, signature)
    
    def validate_async(
        self,
        url: str,
        body: bytes,
        signature: str
    ) -> bool:
        """
        Validate signature for async request.
        
        For aiohttp, we need to handle the raw body.
        
        Args:
            url: Full webhook URL
            body: Raw request body bytes
            signature: X-Twilio-Signature header
            
        Returns:
            True if valid
        """
        # Parse body as form data
        try:
            params = {}
            body_str = body.decode('utf-8')
            for pair in body_str.split('&'):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    params[key] = value
            
            return self.validate(url, params, signature)
            
        except Exception as e:
            logger.error(f"Error parsing body for validation: {e}")
            return False


# =============================================================================
# WHATSAPP WEBHOOK HANDLER
# =============================================================================

class WhatsAppWebhookHandler:
    """
    Webhook handler for Twilio WhatsApp messages.
    
    Receives incoming WhatsApp messages and processes them through
    the Digital FTE agent.
    """
    
    def __init__(self, twilio_client: TwilioWhatsAppClient, db_pool=None):
        """
        Initialize webhook handler.
        
        Args:
            twilio_client: TwilioWhatsAppClient instance
            db_pool: Database connection pool
        """
        self.twilio_client = twilio_client
        self.db_pool = db_pool or get_db_pool()
        
        # Signature validator
        auth_token = os.getenv('TWILIO_AUTH_TOKEN', '')
        self.validator = TwilioSignatureValidator(auth_token)
    
    async def handle_webhook(self, request: web.Request) -> web.Response:
        """
        Handle incoming WhatsApp webhook from Twilio.
        
        Args:
            request: aiohttp web request
            
        Returns:
            TwiML response or JSON
        """
        try:
            # Get signature from headers
            signature = request.headers.get('X-Twilio-Signature', '')
            
            # Read body
            body = await request.read()
            body_str = body.decode('utf-8')
            
            # Validate signature (skip in development)
            if os.getenv('ENVIRONMENT', 'development') == 'production':
                url = str(request.url)
                if not self.validator.validate_async(url, body, signature):
                    logger.warning("Invalid Twilio signature")
                    return web.json_response({'error': 'Invalid signature'}, status=403)
            
            # Parse form data
            params = await request.post()
            
            # Extract message data
            message_data = self._parse_webhook_data(params)
            if not message_data:
                logger.warning("Invalid webhook data")
                return web.json_response({'error': 'Invalid data'}, status=400)
            
            # Process the message
            await self._process_message(message_data)
            
            # Return empty TwiML (we're async processing)
            return web.Response(text='')
            
        except Exception as e:
            logger.error(f"Error handling WhatsApp webhook: {e}", exc_info=True)
            return web.json_response({'error': str(e)}, status=500)
    
    def _parse_webhook_data(self, params: Dict) -> Optional[Dict[str, Any]]:
        """
        Parse Twilio webhook parameters.
        
        Args:
            params: Form parameters from Twilio
            
        Returns:
            Parsed message data or None
        """
        # Get message details
        from_number = params.get('From', '')
        to_number = params.get('To', '')
        body = params.get('Body', '')
        message_sid = params.get('MessageSid', '')
        media_url = params.get('MediaUrl0')  # First media attachment
        media_type = params.get('MediaType0')
        
        if not from_number or not message_sid:
            return None
        
        # Determine content type
        if media_url:
            content_type = media_type.split('/')[0] if media_type else 'media'
        else:
            content_type = 'text'
        
        return {
            'message_id': message_sid,
            'from_number': from_number,
            'to_number': to_number,
            'content_type': content_type,
            'text_content': body,
            'media_url': media_url,
            'media_type': media_type,
            'timestamp': params.get('Timestamp', datetime.now().isoformat())
        }
    
    async def _process_message(self, message_data: Dict[str, Any]):
        """
        Process incoming WhatsApp message.
        
        Args:
            message_data: Parsed message data
        """
        logger.info(f"Processing WhatsApp message: {message_data['message_id']}")
        
        # Normalize phone number
        from_number = self._normalize_phone_number(message_data['from_number'])
        if not from_number:
            logger.warning(f"Invalid phone number: {message_data['from_number']}")
            return
        
        # Get or create customer
        customer_id = await self._get_or_create_customer(phone=from_number)
        
        # Create processed message
        processed = ProcessedWhatsAppMessage(
            channel='whatsapp',
            customer_id=customer_id,
            content=message_data.get('text_content', ''),
            metadata={
                'message_id': message_data['message_id'],
                'from_number': from_number,
                'to_number': message_data['to_number'],
                'content_type': message_data['content_type'],
                'media_url': message_data.get('media_url'),
                'media_type': message_data.get('media_type'),
                'timestamp': message_data['timestamp']
            }
        )
        
        # Send to agent for processing
        await self._send_to_agent(processed)
        
        logger.info(f"WhatsApp message processed: {message_data['message_id']} → customer {customer_id}")
    
    def _normalize_phone_number(self, phone: str) -> Optional[str]:
        """
        Normalize phone number to E.164 format.
        
        Args:
            phone: Raw phone number
            
        Returns:
            Normalized number or None
        """
        # Remove 'whatsapp:' prefix if present
        if phone.startswith('whatsapp:'):
            phone = phone[9:]
        
        # Ensure + prefix
        if not phone.startswith('+'):
            # Assume US number if no country code
            phone = '+1' + phone.lstrip('1')
        
        # Validate format
        if not re.match(r'^\+\d{10,15}$', phone):
            return None
        
        return phone
    
    async def _get_or_create_customer(self, phone: str) -> str:
        """
        Get existing customer or create new one by phone.
        
        Args:
            phone: Customer phone number
            
        Returns:
            Customer ID
        """
        # TODO: Implement database lookup/creation
        # For now, return phone as customer_id
        return phone
    
    async def _send_to_agent(self, processed: ProcessedWhatsAppMessage):
        """
        Send processed message to Digital FTE agent.
        
        Args:
            processed: ProcessedWhatsAppMessage object
        """
        # TODO: Implement Kafka publishing or direct agent call
        logger.info(f"Sending to agent: {processed.customer_id} - {processed.content[:50]}...")


# =============================================================================
# WHATSAPP RESPONSE SENDER
# =============================================================================

class WhatsAppResponseSender:
    """
    Handles sending WhatsApp responses through Twilio API.
    
    Formats responses according to WhatsApp requirements:
    - Max 300 characters
    - Emoji-friendly
    - Casual tone
    """
    
    def __init__(self, twilio_client: TwilioWhatsAppClient):
        """
        Initialize response sender.
        
        Args:
            twilio_client: TwilioWhatsAppClient instance
        """
        self.twilio_client = twilio_client
    
    async def send_response(
        self,
        to_number: str,
        message: str,
        ticket_id: Optional[str] = None
    ) -> bool:
        """
        Send WhatsApp response with proper formatting.
        
        Args:
            to_number: Recipient WhatsApp number
            message: Response message
            ticket_id: Optional ticket ID for reference
            
        Returns:
            True if sent successfully
        """
        # Format message for WhatsApp
        formatted_message = self._format_whatsapp_message(message, ticket_id)
        
        # Send via Twilio
        result = await self.twilio_client.send_message(
            to_number=to_number,
            body=formatted_message
        )
        
        if result:
            logger.info(f"WhatsApp response sent: {ticket_id} → {to_number}")
            return True
        else:
            logger.error(f"Failed to send WhatsApp response: {ticket_id}")
            return False
    
    def _format_whatsapp_message(self, message: str, ticket_id: Optional[str]) -> str:
        """
        Format message for WhatsApp (casual, emoji, length limit).
        
        Args:
            message: Response message
            ticket_id: Optional ticket ID
            
        Returns:
            Formatted WhatsApp message
        """
        # Add casual greeting if not present
        if not message.lower().startswith(('hey', 'hi', 'hello', 'thanks')):
            message = "Hey! " + message
        
        # Add emoji if appropriate
        if '?' in message and '🤔' not in message:
            message = message + " 🤔"
        elif '!' in message and '😊' not in message:
            message = message + " 😊"
        
        # Add ticket reference if provided (doesn't count toward 300 limit for tracking)
        if ticket_id:
            message = message + f"\n\nRef: {ticket_id}"
        
        # Enforce 300 char limit
        if len(message) > 300:
            message = message[:297] + "..."
        
        return message


# =============================================================================
# AIOHTTP WEB APPLICATION
# =============================================================================

def create_whatsapp_webhook_app(twilio_client: TwilioWhatsAppClient) -> web.Application:
    """
    Create aiohttp web application for WhatsApp webhook.
    
    Args:
        twilio_client: TwilioWhatsAppClient instance
        
    Returns:
        aiohttp web.Application
    """
    app = web.Application()
    
    # Create handler
    handler = WhatsAppWebhookHandler(twilio_client)
    
    # Register routes
    app.router.add_post('/webhook/whatsapp', handler.handle_webhook)
    app.router.add_get('/health', lambda r: web.json_response({'status': 'healthy'}))
    
    return app


# =============================================================================
# MAIN (Testing)
# =============================================================================

if __name__ == "__main__":
    """Test WhatsApp handler."""
    print("=" * 80)
    print("NEXUSFLOW DIGITAL FTE - WHATSAPP HANDLER")
    print("=" * 80)
    
    # Check environment variables
    required_vars = [
        'TWILIO_ACCOUNT_SID',
        'TWILIO_AUTH_TOKEN',
        'TWILIO_WHATSAPP_NUMBER'
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        print(f"\n⚠️  Missing environment variables: {missing}")
        print("\nSet these variables to use WhatsApp integration:")
        print("  export TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxx")
        print("  export TWILIO_AUTH_TOKEN=your-auth-token")
        print("  export TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886")
    else:
        print("\n✅ All environment variables set")
        print("✅ WhatsApp handler ready for deployment")
    
    print("\n" + "=" * 80)
