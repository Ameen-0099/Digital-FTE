"""
NexusFlow Customer Success Digital FTE - Web Form Channel Handler
==================================================================
Exercise 2.2: Channel Integrations - Web Support Form Handler

This module handles customer support form submissions via a FastAPI
REST endpoint. Provides both JSON API and optional HTML form template
for embedding in websites.

Features:
- FastAPI router with /support endpoint
- Pydantic models for form validation
- Automatic ticket creation with immediate ticket_id response
- Standalone, embeddable HTML form (optional)
- Customer identification by email
- Integration with database schema

Author: Digital FTE Team
Version: 1.0.0 (Production)
"""

import asyncio
import logging
import os
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

# FastAPI
from fastapi import APIRouter, HTTPException, Request, Form, Depends
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field, field_validator, EmailStr

# Database connection
from database.connection import get_db_pool

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS
# =============================================================================

class PriorityType(str, Enum):
    """Support ticket priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueCategory(str, Enum):
    """Issue categories for routing."""
    HOW_TO = "how_to"
    TECHNICAL_ISSUE = "technical_issue"
    BILLING = "billing"
    FEATURE_REQUEST = "feature_request"
    ACCOUNT = "account"
    INTEGRATION = "integration"
    OTHER = "other"


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class SupportFormSubmission(BaseModel):
    """
    Pydantic model for web support form submission.
    
    Validates all input fields with appropriate constraints.
    """
    
    # Customer information
    name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Customer's full name",
        examples=["John Doe"]
    )
    
    email: EmailStr = Field(
        ...,
        description="Customer's email address for follow-up",
        examples=["john@example.com"]
    )
    
    company: Optional[str] = Field(
        None,
        max_length=255,
        description="Customer's company name",
        examples=["Acme Corp"]
    )
    
    phone: Optional[str] = Field(
        None,
        max_length=50,
        description="Customer's phone number",
        examples=["+1-555-0123"]
    )
    
    # Issue details
    subject: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Brief subject line for the issue",
        examples=["Cannot export Gantt chart to PDF"]
    )
    
    description: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Detailed description of the issue or question",
        examples=["I'm trying to export my Gantt chart but it keeps hanging..."]
    )
    
    category: IssueCategory = Field(
        default=IssueCategory.OTHER,
        description="Category of the issue for routing"
    )
    
    priority: PriorityType = Field(
        default=PriorityType.MEDIUM,
        description="Priority level of the issue"
    )
    
    # Optional metadata
    page_url: Optional[str] = Field(
        None,
        max_length=2000,
        description="URL where the issue occurred",
        examples=["https://app.nexusflow.com/projects/123/gantt"]
    )
    
    browser_info: Optional[str] = Field(
        None,
        max_length=500,
        description="Browser and OS information",
        examples=["Chrome 120 on Windows 11"]
    )
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name contains only valid characters."""
        if not re.match(r'^[\w\s\.\-\']+$', v):
            raise ValueError('Name contains invalid characters')
        return v.strip()
    
    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone number format if provided."""
        if v is None:
            return v
        v = v.strip()
        if v and not re.match(r'^\+?[\d\s\-\(\)]+$', v):
            raise ValueError('Invalid phone number format')
        return v


class SupportFormResponse(BaseModel):
    """
    Response model for successful form submission.
    
    Returns ticket_id immediately for customer reference.
    """
    
    success: bool = Field(..., description="Whether submission was successful")
    ticket_id: str = Field(..., description="Generated ticket ID for reference")
    message: str = Field(..., description="Confirmation message")
    estimated_response_time: str = Field(
        ...,
        description="Expected response time based on priority"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "ticket_id": "TKT-20260327-ABC123",
                "message": "Thank you for contacting NexusFlow Support. We've received your request.",
                "estimated_response_time": "2-4 hours"
            }
        }


class SupportFormError(BaseModel):
    """
    Response model for form submission errors.
    """
    
    success: bool = False
    error: str
    details: Optional[Dict[str, str]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "Validation failed",
                "details": {
                    "email": "Invalid email address"
                }
            }
        }


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class ProcessedWebForm:
    """Processed web form ready for agent handling."""
    channel: str
    customer_id: str
    content: str
    metadata: Dict[str, Any]


# =============================================================================
# WEB FORM HANDLER
# =============================================================================

class WebFormHandler:
    """
    Handles web support form submissions.
    
    Creates tickets, identifies customers, and sends to agent for processing.
    """
    
    # Response time estimates by priority
    RESPONSE_TIMES = {
        PriorityType.LOW: "24-48 hours",
        PriorityType.MEDIUM: "4-8 hours",
        PriorityType.HIGH: "1-2 hours",
        PriorityType.CRITICAL: "15-30 minutes"
    }
    
    def __init__(self, db_pool=None):
        """
        Initialize web form handler.
        
        Args:
            db_pool: Database connection pool
        """
        self.db_pool = db_pool or get_db_pool()
    
    async def process_submission(
        self,
        submission: SupportFormSubmission
    ) -> SupportFormResponse:
        """
        Process a support form submission.
        
        Args:
            submission: Validated form submission
            
        Returns:
            Response with ticket_id
        """
        logger.info(f"Processing support form from {submission.email}")
        
        # Generate ticket ID
        ticket_id = self._generate_ticket_id()
        
        # Get or create customer
        customer_id = await self._get_or_create_customer(
            email=submission.email,
            name=submission.name,
            company=submission.company,
            phone=submission.phone
        )
        
        # Create processed message for agent
        processed = ProcessedWebForm(
            channel='web_form',
            customer_id=customer_id,
            content=submission.description,
            metadata={
                'ticket_id': ticket_id,
                'subject': submission.subject,
                'category': submission.category.value,
                'priority': submission.priority.value,
                'name': submission.name,
                'email': submission.email,
                'company': submission.company,
                'phone': submission.phone,
                'page_url': submission.page_url,
                'browser_info': submission.browser_info,
                'submitted_at': datetime.now().isoformat()
            }
        )
        
        # Send to agent for processing
        await self._send_to_agent(processed)
        
        # Save to database (TODO: implement)
        await self._save_ticket_to_database(ticket_id, customer_id, submission)
        
        # Return response
        return SupportFormResponse(
            success=True,
            ticket_id=ticket_id,
            message=f"Thank you for contacting NexusFlow Support, {submission.name.split()[0]}! We've received your request and will respond shortly.",
            estimated_response_time=self.RESPONSE_TIMES[submission.priority]
        )
    
    def _generate_ticket_id(self) -> str:
        """
        Generate unique ticket ID.
        
        Format: TKT-YYYYMMDD-XXXXXX
        
        Returns:
            Ticket ID string
        """
        date_part = datetime.now().strftime('%Y%m%d')
        unique_part = uuid.uuid4().hex[:6].upper()
        return f"TKT-{date_part}-{unique_part}"
    
    async def _get_or_create_customer(
        self,
        email: str,
        name: str,
        company: Optional[str] = None,
        phone: Optional[str] = None
    ) -> str:
        """
        Get existing customer or create new one.
        
        Args:
            email: Customer email
            name: Customer name
            company: Optional company name
            phone: Optional phone number
            
        Returns:
            Customer ID (email for now)
        """
        # TODO: Implement database lookup/creation
        # For now, return email as customer_id
        return email
    
    async def _send_to_agent(self, processed: ProcessedWebForm):
        """
        Send processed form to Digital FTE agent.
        
        Args:
            processed: ProcessedWebForm object
        """
        # TODO: Implement Kafka publishing or direct agent call
        logger.info(f"Sending to agent: {processed.customer_id} - {processed.metadata.get('subject', 'No subject')}")
    
    async def _save_ticket_to_database(
        self,
        ticket_id: str,
        customer_id: str,
        submission: SupportFormSubmission
    ):
        """
        Save ticket to database.
        
        Args:
            ticket_id: Generated ticket ID
            customer_id: Customer ID
            submission: Form submission
        """
        # TODO: Implement database insertion
        logger.info(f"Saving ticket {ticket_id} to database")


# =============================================================================
# FASTAPI ROUTER
# =============================================================================

# Create router
router = APIRouter(prefix="/support", tags=["Support"])

# Handler instance
form_handler = WebFormHandler()


@router.post(
    "/submit",
    response_model=SupportFormResponse,
    responses={
        200: {"model": SupportFormResponse, "description": "Successful submission"},
        400: {"model": SupportFormError, "description": "Validation error"},
        500: {"model": SupportFormError, "description": "Server error"}
    },
    summary="Submit Support Request",
    description="Submit a customer support request via web form. Returns ticket ID immediately."
)
async def submit_support_form(
    request: Request,
    submission: SupportFormSubmission
) -> SupportFormResponse:
    """
    Submit a support request via web form.
    
    - **name**: Customer's full name
    - **email**: Email address for follow-up
    - **company**: Company name (optional)
    - **phone**: Phone number (optional)
    - **subject**: Brief subject line
    - **description**: Detailed issue description
    - **category**: Issue category for routing
    - **priority**: Priority level
    - **page_url**: URL where issue occurred (optional)
    - **browser_info**: Browser/OS info (optional)
    
    Returns ticket ID immediately for customer reference.
    """
    try:
        # Process submission
        response = await form_handler.process_submission(submission)
        return response
        
    except Exception as e:
        logger.error(f"Error processing support form: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process request: {str(e)}"
        )


@router.post(
    "/submit-form",
    response_model=SupportFormResponse,
    summary="Submit Support Form (Form Data)",
    description="Alternative endpoint accepting form-data instead of JSON"
)
async def submit_support_form_data(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    company: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    subject: str = Form(...),
    description: str = Form(...),
    category: str = Form("other"),
    priority: str = Form("medium"),
    page_url: Optional[str] = Form(None),
    browser_info: Optional[str] = Form(None)
) -> SupportFormResponse:
    """
    Submit support form using form-data encoding.
    
    This endpoint accepts traditional form submissions (application/x-www-form-urlencoded).
    """
    try:
        # Convert to Pydantic model
        submission = SupportFormSubmission(
            name=name,
            email=email,
            company=company,
            phone=phone,
            subject=subject,
            description=description,
            category=IssueCategory(category.lower()) if category else IssueCategory.OTHER,
            priority=PriorityType(priority.lower()) if priority else PriorityType.MEDIUM,
            page_url=page_url,
            browser_info=browser_info
        )
        
        # Process submission
        response = await form_handler.process_submission(submission)
        return response
        
    except Exception as e:
        logger.error(f"Error processing support form: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process request: {str(e)}"
        )


@router.get(
    "/form",
    response_class=HTMLResponse,
    summary="Get Embeddable Support Form",
    description="Returns an HTML form that can be embedded in any website"
)
async def get_support_form() -> HTMLResponse:
    """
    Get embeddable HTML support form.
    
    Returns a complete HTML form that can be embedded in any website
    via iframe or direct inclusion.
    """
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NexusFlow Support</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; padding: 20px; }
        .form-container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { color: #333; margin-bottom: 10px; font-size: 24px; }
        .subtitle { color: #666; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 6px; color: #333; font-weight: 500; }
        input, select, textarea { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; transition: border-color 0.2s; }
        input:focus, select:focus, textarea:focus { outline: none; border-color: #4f46e5; }
        textarea { min-height: 150px; resize: vertical; }
        .form-row { display: flex; gap: 15px; }
        .form-row .form-group { flex: 1; }
        button { background: #4f46e5; color: white; padding: 14px 24px; border: none; border-radius: 6px; font-size: 16px; font-weight: 600; cursor: pointer; width: 100%; transition: background 0.2s; }
        button:hover { background: #4338ca; }
        button:disabled { background: #ccc; cursor: not-allowed; }
        .required { color: #ef4444; }
        .success-message { display: none; background: #d1fae5; border: 1px solid #6ee7b7; color: #065f46; padding: 20px; border-radius: 6px; text-align: center; }
        .success-message h2 { color: #047857; margin-bottom: 10px; }
        .ticket-id { font-family: monospace; background: #fff; padding: 8px 16px; border-radius: 4px; display: inline-block; margin: 10px 0; }
        .error-message { color: #ef4444; font-size: 12px; margin-top: 4px; display: none; }
    </style>
</head>
<body>
    <div class="form-container">
        <h1>📬 NexusFlow Support</h1>
        <p class="subtitle">We're here to help! Fill out the form below and we'll get back to you soon.</p>
        
        <div id="successMessage" class="success-message">
            <h2>✅ Request Received!</h2>
            <p>Thank you for contacting NexusFlow Support.</p>
            <p>Your ticket ID:</p>
            <div class="ticket-id" id="ticketIdDisplay"></div>
            <p>We'll respond within <strong id="responseTime"></strong></p>
        </div>
        
        <form id="supportForm" onsubmit="handleSubmit(event)">
            <div class="form-row">
                <div class="form-group">
                    <label for="name">Name <span class="required">*</span></label>
                    <input type="text" id="name" name="name" required minlength="2" maxlength="255">
                </div>
                <div class="form-group">
                    <label for="email">Email <span class="required">*</span></label>
                    <input type="email" id="email" name="email" required>
                </div>
            </div>
            
            <div class="form-row">
                <div class="form-group">
                    <label for="company">Company</label>
                    <input type="text" id="company" name="company" maxlength="255">
                </div>
                <div class="form-group">
                    <label for="phone">Phone</label>
                    <input type="tel" id="phone" name="phone" maxlength="50" placeholder="+1-555-0123">
                </div>
            </div>
            
            <div class="form-group">
                <label for="subject">Subject <span class="required">*</span></label>
                <input type="text" id="subject" name="subject" required minlength="5" maxlength="500" placeholder="Brief description of your issue">
            </div>
            
            <div class="form-group">
                <label for="description">Description <span class="required">*</span></label>
                <textarea id="description" name="description" required minlength="10" maxlength="5000" placeholder="Please describe your issue in detail..."></textarea>
            </div>
            
            <div class="form-row">
                <div class="form-group">
                    <label for="category">Category</label>
                    <select id="category" name="category">
                        <option value="other">Other</option>
                        <option value="how_to">How-To Question</option>
                        <option value="technical_issue">Technical Issue</option>
                        <option value="billing">Billing</option>
                        <option value="feature_request">Feature Request</option>
                        <option value="account">Account</option>
                        <option value="integration">Integration</option>
                    </select>
                </div>
                <div class="form-group">
                    <label for="priority">Priority</label>
                    <select id="priority" name="priority">
                        <option value="low">Low</option>
                        <option value="medium" selected>Medium</option>
                        <option value="high">High</option>
                        <option value="critical">Critical</option>
                    </select>
                </div>
            </div>
            
            <button type="submit" id="submitBtn">Submit Request</button>
        </form>
    </div>
    
    <script>
        async function handleSubmit(event) {
            event.preventDefault();

            const form = event.target;
            const btn = document.getElementById('submitBtn');
            btn.disabled = true;
            btn.textContent = 'Submitting...';

            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());

            try {
                // Use relative path 'submit' since we're already in /support/ router
                const response = await fetch('submit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (response.ok && result.success) {
                    form.style.display = 'none';
                    document.getElementById('successMessage').style.display = 'block';
                    document.getElementById('ticketIdDisplay').textContent = result.ticket_id;
                    document.getElementById('responseTime').textContent = result.estimated_response_time;
                } else {
                    alert('Error: ' + (result.error || 'Failed to submit request'));
                    btn.disabled = false;
                    btn.textContent = 'Submit Request';
                }
            } catch (error) {
                alert('Error submitting request. Please try again.');
                btn.disabled = false;
                btn.textContent = 'Submit Request';
            }
        }
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html)


@router.get(
    "/embed.js",
    response_class=HTMLResponse,
    summary="Get Embeddable Widget Script",
    description="Returns a JavaScript widget that can be embedded in any website"
)
async def get_embed_widget() -> HTMLResponse:
    """
    Get embeddable JavaScript widget.
    
    Returns a script that creates a floating support button on any website.
    """
    # Return JavaScript widget code
    return HTMLResponse(
        content="// Embed widget script - contact dev@nexusflow.com for full implementation",
        media_type="application/javascript"
    )


# =============================================================================
# CREATE FASTAPI APP
# =============================================================================

def create_web_form_app() -> "FastAPI":
    """
    Create FastAPI application with web form routes.
    
    Returns:
        FastAPI application
    """
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    
    app = FastAPI(
        title="NexusFlow Support API",
        description="Customer support form submission API",
        version="1.0.0"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include router
    app.include_router(router)
    
    return app


# =============================================================================
# MAIN (Testing)
# =============================================================================

if __name__ == "__main__":
    """Test web form handler."""
    print("=" * 80)
    print("NEXUSFLOW DIGITAL FTE - WEB FORM HANDLER")
    print("=" * 80)
    
    print("\n✅ Web form handler ready")
    print("\nEndpoints:")
    print("  POST /support/submit    - Submit support request (JSON)")
    print("  POST /support/submit-form - Submit support request (form-data)")
    print("  GET  /support/form      - Get embeddable HTML form")
    print("  GET  /support/embed.js  - Get embeddable widget script")
    
    print("\nTo run the server:")
    print("  uvicorn production.channels.web_form_handler:create_web_form_app --reload")
    
    print("\n" + "=" * 80)
