"""
NexusFlow Customer Success Digital FTE - Production Tools
==========================================================
Transition Step 3: OpenAI Agents SDK @function_tool Implementation

This module contains production-ready tool functions for the NexusFlow
Customer Success Digital FTE. Each tool is decorated with @function_tool
from the OpenAI Agents SDK and includes:

- Strict Pydantic input schemas for validation
- Comprehensive docstrings for LLM consumption
- Error handling with graceful fallbacks
- PostgreSQL integration placeholders (to be implemented)
- Structured, agent-friendly return values

Author: Digital FTE Team
Version: 1.0.0 (Production)
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

# OpenAI Agents SDK imports
from agents import function_tool

# Pydantic imports for schema validation
from pydantic import BaseModel, Field, field_validator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# PYDANTIC MODELS - Input/Output Schemas
# =============================================================================

class ChannelType(str, Enum):
    """Supported communication channels."""
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    WEB_FORM = "web_form"


class PriorityLevel(str, Enum):
    """Ticket priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class UrgencyLevel(str, Enum):
    """Escalation urgency levels."""
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class KnowledgeArticle(BaseModel):
    """Single knowledge base article."""
    key: str = Field(..., description="Article identifier")
    title: str = Field(..., description="Article title")
    content: str = Field(..., description="Article content")
    score: float = Field(..., description="Relevance score (higher = more relevant)")


class SearchKnowledgeBaseOutput(BaseModel):
    """Output schema for knowledge base search."""
    query: str = Field(..., description="Original search query")
    results_count: int = Field(..., description="Number of articles found")
    articles: List[KnowledgeArticle] = Field(default_factory=list)
    confidence: float = Field(..., description="Overall confidence (0.0-1.0)")
    has_relevant_result: bool = Field(..., description="Whether any article is relevant")
    error: Optional[str] = Field(None, description="Error message if search failed")


class CreateTicketOutput(BaseModel):
    """Output schema for ticket creation."""
    success: bool = Field(..., description="Whether ticket was created")
    ticket_id: Optional[str] = Field(None, description="Generated ticket ID")
    customer_id: str = Field(..., description="Customer identifier")
    subject: str = Field(..., description="Ticket subject")
    status: str = Field(..., description="Initial ticket status")
    created_at: str = Field(..., description="ISO timestamp of creation")
    conversation_id: Optional[str] = Field(None, description="Linked conversation ID")
    error: Optional[str] = Field(None, description="Error message if creation failed")


class CustomerHistorySummary(BaseModel):
    """Customer history summary."""
    total_conversations: int = Field(..., description="Number of conversations")
    total_messages: int = Field(..., description="Total messages exchanged")
    topics_discussed: List[str] = Field(default_factory=list)
    current_sentiment: str = Field(..., description="Current sentiment label")
    sentiment_trend: str = Field(..., description="Sentiment trend")
    channel_history: List[str] = Field(default_factory=list)
    last_interaction: str = Field(..., description="ISO timestamp of last interaction")
    status: str = Field(..., description="Current ticket status")


class GetCustomerHistoryOutput(BaseModel):
    """Output schema for customer history retrieval."""
    found: bool = Field(..., description="Whether customer was found")
    customer_id: str = Field(..., description="Customer identifier")
    name: Optional[str] = Field(None, description="Customer name")
    email: Optional[str] = Field(None, description="Customer email")
    company: Optional[str] = Field(None, description="Customer company")
    plan: Optional[str] = Field(None, description="Customer plan")
    is_vip: bool = Field(default=False, description="Whether customer is VIP")
    history_summary: Optional[CustomerHistorySummary] = Field(None)
    is_new_customer: bool = Field(..., description="Whether this is first interaction")
    error: Optional[str] = Field(None, description="Error message if retrieval failed")


class EscalateToHumanOutput(BaseModel):
    """Output schema for escalation."""
    success: bool = Field(..., description="Whether escalation was created")
    escalation_id: Optional[str] = Field(None, description="Generated escalation ID")
    ticket_id: str = Field(..., description="Escalated ticket ID")
    escalation_level: str = Field(..., description="Assigned escalation level (L1-L4)")
    urgency: str = Field(..., description="Escalation urgency")
    status: str = Field(..., description="Escalation status")
    created_at: str = Field(..., description="ISO timestamp of creation")
    reason: str = Field(..., description="Escalation reason")
    error: Optional[str] = Field(None, description="Error message if escalation failed")


class SendResponseOutput(BaseModel):
    """Output schema for sending response."""
    success: bool = Field(..., description="Whether response was sent")
    ticket_id: str = Field(..., description="Ticket ID")
    message_id: Optional[str] = Field(None, description="Generated message ID")
    channel: str = Field(..., description="Channel used")
    status: str = Field(..., description="Delivery status")
    delivered_at: str = Field(..., description="ISO timestamp of delivery")
    message_length: int = Field(..., description="Length of message")
    error: Optional[str] = Field(None, description="Error message if sending failed")


# =============================================================================
# KNOWLEDGE BASE (In-memory for demo)
# =============================================================================

KNOWLEDGE_BASE = {
    "getting_started": {
        "title": "Getting Started with NexusFlow",
        "content": "To create your account: Visit app.nexusflow.com, click 'Start Free Trial', enter your work email, verify, and complete onboarding.",
        "keywords": ["signup", "register", "create account", "getting started", "onboarding", "setup"]
    },
    "pricing": {
        "title": "NexusFlow Pricing Plans",
        "content": "Free Plan ($0): 3 projects. Starter ($12): Unlimited projects, Gantt charts. Professional ($24): 100GB storage, time tracking. Business ($45): Advanced analytics. Enterprise (Custom): SSO/SAML.",
        "keywords": ["pricing", "cost", "price", "plan", "upgrade", "subscription", "tier"]
    },
    "billing_help": {
        "title": "Billing Support & Payment Issues",
        "content": "For billing issues: If you see duplicate charges, contact support immediately. Provide transaction IDs. Refunds processed within 3-5 business days. Download invoices from Settings → Billing.",
        "keywords": ["billing", "charge", "payment", "invoice", "refund", "duplicate", "transaction"]
    },
    "recurring_tasks": {
        "title": "Setting Up Recurring Tasks",
        "content": "To create a recurring task: 1. Open the task. 2. Click 'Repeat'. 3. Choose frequency: Daily, Weekly, Bi-weekly, Monthly. 4. Select the day. 5. Click 'Save'.",
        "keywords": ["recurring", "repeat", "schedule", "automatic", "periodic"]
    },
    "gantt_export": {
        "title": "Exporting Gantt Charts",
        "content": "To export Gantt to PDF: 1. Open project. 2. Switch to Gantt view. 3. Click 'Export'. 4. Select 'PDF'. 5. Click 'Export'. Troubleshooting: Clear cache, use Chrome.",
        "keywords": ["export", "gantt", "pdf", "download", "print", "report"]
    },
    "integrations": {
        "title": "NexusFlow Integrations",
        "content": "Popular Integrations: Slack, Google Calendar, GitHub/GitLab, Salesforce, Zapier/Make (5000+ apps). API Access: REST API available for all plans.",
        "keywords": ["integration", "slack", "calendar", "github", "salesforce", "api", "connect"]
    },
    "mobile_app": {
        "title": "Mobile App Guide",
        "content": "Mobile App Features: View/edit tasks, push notifications, comment/attach photos, time timer. Troubleshooting: Update app, clear cache, reinstall.",
        "keywords": ["mobile", "app", "ios", "android", "phone", "tablet", "crash"]
    },
    "data_recovery": {
        "title": "Data Recovery & Deleted Items",
        "content": "Recovering Deleted Data: Go to Settings → Data → Recently Deleted. Items retained 30 days. Click 'Restore'. For urgent recovery, contact support.",
        "keywords": ["deleted", "recovery", "restore", "disappeared", "missing", "recover"]
    }
}


# =============================================================================
# PRODUCTION TOOLS - @function_tool Decorated Functions
# =============================================================================

@function_tool
async def search_knowledge_base(query: str) -> str:
    """
    Search the NexusFlow knowledge base for relevant documentation.

    USE THIS TOOL WHEN:
    - Customer asks a product question ("How do I...?")
    - Customer reports a technical issue
    - Customer needs troubleshooting guidance

    Args:
        query: The search query from the customer message.

    Returns:
        JSON string with query, results_count, articles, confidence, has_relevant_result
    """
    try:
        logger.info(f"Searching knowledge base for query: {query}")

        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        query_lower = query.lower()
        results = []

        for key, article in KNOWLEDGE_BASE.items():
            score = 0
            if key.replace("_", " ") in query_lower:
                score += 3
            for keyword in article["keywords"]:
                if keyword in query_lower:
                    score += 2
            if any(word in article["content"].lower() for word in query_lower.split()):
                score += 1

            if score > 0:
                results.append({"key": key, "title": article["title"], 
                               "content": article["content"], "score": score})

        results.sort(key=lambda x: x["score"], reverse=True)
        top_results = results[:3]
        confidence = min(1.0, top_results[0]["score"] / 10.0) if top_results else 0.0

        output = SearchKnowledgeBaseOutput(
            query=query, results_count=len(top_results),
            articles=[KnowledgeArticle(**r) for r in top_results],
            confidence=confidence, has_relevant_result=confidence > 0.5
        )
        return output.model_dump_json(indent=2)

    except ValueError as e:
        return SearchKnowledgeBaseOutput(
            query=query, results_count=0, articles=[], confidence=0.0,
            has_relevant_result=False, error=str(e)
        ).model_dump_json(indent=2)
    except Exception as e:
        logger.error(f"Unexpected error in search_knowledge_base: {e}", exc_info=True)
        return SearchKnowledgeBaseOutput(
            query=query, results_count=0, articles=[], confidence=0.0,
            has_relevant_result=False, error=f"Search failed: {str(e)}"
        ).model_dump_json(indent=2)


@function_tool
async def create_ticket(customer_id: str, issue: str, priority: str, 
                        channel: str, subject: Optional[str] = None) -> str:
    """
    Create a new support ticket in the NexusFlow system.

    Args:
        customer_id: Customer identifier (email or phone)
        issue: Description of the customer's issue
        priority: "low", "medium", "high", or "critical"
        channel: "email", "whatsapp", or "web_form"
        subject: Optional subject line

    Returns:
        JSON string with success, ticket_id, customer_id, subject, status, created_at
    """
    try:
        logger.info(f"Creating ticket for customer {customer_id}, priority: {priority}")

        if not customer_id or not customer_id.strip():
            raise ValueError("customer_id is required")
        if not issue or len(issue.strip()) < 10:
            raise ValueError("issue must be at least 10 characters")
        if priority not in ["low", "medium", "high", "critical"]:
            raise ValueError("priority must be low, medium, high, or critical")
        if channel not in ["email", "whatsapp", "web_form"]:
            raise ValueError("channel must be email, whatsapp, or web_form")

        ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d')}-{id(customer_id) % 1000000:06X}"
        if not subject:
            subject = issue[:50] + "..." if len(issue) > 50 else issue

        conversation_id = f"CONV-{datetime.now().strftime('%Y%m%d')}-{customer_id[:8]}"
        created_at = datetime.now().isoformat()

        output = CreateTicketOutput(
            success=True, ticket_id=ticket_id, customer_id=customer_id,
            subject=subject, status="open", created_at=created_at,
            conversation_id=conversation_id
        )
        return output.model_dump_json(indent=2)

    except ValueError as e:
        return CreateTicketOutput(
            success=False, ticket_id=None, customer_id=customer_id,
            subject=subject or "", status="", created_at="", error=str(e)
        ).model_dump_json(indent=2)
    except Exception as e:
        logger.error(f"Unexpected error in create_ticket: {e}", exc_info=True)
        return CreateTicketOutput(
            success=False, ticket_id=None, customer_id=customer_id,
            subject=subject or "", status="", created_at="",
            error=f"Ticket creation failed: {str(e)}"
        ).model_dump_json(indent=2)


@function_tool
async def get_customer_history(customer_id: str) -> str:
    """
    Retrieve complete customer interaction history across ALL channels.

    Args:
        customer_id: Customer identifier (email or phone)

    Returns:
        JSON string with found, customer_id, name, email, company, plan, is_vip, etc.
    """
    try:
        logger.info(f"Retrieving history for customer {customer_id}")

        if not customer_id or not customer_id.strip():
            raise ValueError("customer_id is required")

        known_customers = {
            "alice@techcorp.com": {"name": "Alice Johnson", "company": "TechCorp Inc.", 
                                   "plan": "Professional", "total_messages": 6,
                                   "topics": ["export", "performance"], "sentiment": "panicked",
                                   "trend": "stable", "channels": ["email"], "status": "escalated"},
            "bob@startup.io": {"name": "Bob Martinez", "company": "StartupIO", 
                              "plan": "Starter", "total_messages": 6,
                              "topics": ["recurring_tasks", "time_tracking"], "sentiment": "neutral",
                              "trend": "declining", "channels": ["web_form", "whatsapp"], 
                              "status": "in_progress"},
            "carol@enterprise.com": {"name": "Carol White", "company": "Enterprise Corp", 
                                     "plan": "Business", "total_messages": 6,
                                     "topics": ["billing", "pricing"], "sentiment": "concerned",
                                     "trend": "stable", "channels": ["email"], "status": "escalated"}
        }

        customer_data = known_customers.get(customer_id)

        if not customer_data:
            output = GetCustomerHistoryOutput(
                found=False, customer_id=customer_id, name=None,
                email=customer_id if "@" in customer_id else None,
                company=None, plan=None, is_vip=False, history_summary=None,
                is_new_customer=True
            )
            return output.model_dump_json(indent=2)

        output = GetCustomerHistoryOutput(
            found=True, customer_id=customer_id, name=customer_data["name"],
            email=customer_id if "@" in customer_id else None,
            company=customer_data["company"], plan=customer_data["plan"],
            is_vip=customer_data["plan"] == "Enterprise",
            history_summary=CustomerHistorySummary(
                total_conversations=1, total_messages=customer_data["total_messages"],
                topics_discussed=customer_data["topics"],
                current_sentiment=customer_data["sentiment"],
                sentiment_trend=customer_data["trend"],
                channel_history=customer_data["channels"],
                last_interaction=datetime.now().isoformat(),
                status=customer_data["status"]
            ),
            is_new_customer=False
        )
        return output.model_dump_json(indent=2)

    except ValueError as e:
        return GetCustomerHistoryOutput(
            found=False, customer_id=customer_id, name=None, email=None,
            company=None, plan=None, is_vip=False, history_summary=None,
            is_new_customer=True, error=str(e)
        ).model_dump_json(indent=2)
    except Exception as e:
        logger.error(f"Unexpected error in get_customer_history: {e}", exc_info=True)
        return GetCustomerHistoryOutput(
            found=False, customer_id=customer_id, name=None, email=None,
            company=None, plan=None, is_vip=False, history_summary=None,
            is_new_customer=True, error=f"History retrieval failed: {str(e)}"
        ).model_dump_json(indent=2)


@function_tool
async def escalate_to_human(ticket_id: str, reason: str, urgency: str = "normal") -> str:
    """
    Escalate a ticket to human support when AI cannot resolve the issue.

    Args:
        ticket_id: The ID of the ticket to escalate
        reason: Specific reason for escalation
        urgency: "normal" (default), "high", or "critical"

    Returns:
        JSON string with success, escalation_id, ticket_id, escalation_level, etc.
    """
    try:
        logger.info(f"Escalating ticket {ticket_id} - reason: {reason}, urgency: {urgency}")

        if not ticket_id or not ticket_id.strip():
            raise ValueError("ticket_id is required")
        if not reason or len(reason.strip()) < 10:
            raise ValueError("reason must be at least 10 characters")
        if urgency not in ["normal", "high", "critical"]:
            raise ValueError("urgency must be normal, high, or critical")

        reason_lower = reason.lower()
        escalation_level = "L1_Tier1"

        if any(word in reason_lower for word in ["legal", "lawsuit", "attorney", "court", "lawyer"]):
            escalation_level = "L4_Management"
        elif any(word in reason_lower for word in ["security", "breach", "unauthorized", "hack"]):
            escalation_level = "L3_Tier3"
        elif any(word in reason_lower for word in ["technical", "integration", "api", "advanced", "vip", "enterprise"]):
            escalation_level = "L2_Tier2"

        escalation_id = f"ESC-{datetime.now().strftime('%Y%m%d')}-{id(ticket_id) % 100000:05X}"
        created_at = datetime.now().isoformat()

        output = EscalateToHumanOutput(
            success=True, escalation_id=escalation_id, ticket_id=ticket_id,
            escalation_level=escalation_level, urgency=urgency, status="pending",
            created_at=created_at, reason=reason
        )
        return output.model_dump_json(indent=2)

    except ValueError as e:
        return EscalateToHumanOutput(
            success=False, escalation_id=None, ticket_id=ticket_id,
            escalation_level="", urgency=urgency, status="", created_at="",
            reason=reason, error=str(e)
        ).model_dump_json(indent=2)
    except Exception as e:
        logger.error(f"Unexpected error in escalate_to_human: {e}", exc_info=True)
        return EscalateToHumanOutput(
            success=False, escalation_id=None, ticket_id=ticket_id,
            escalation_level="", urgency=urgency, status="", created_at="",
            reason=reason, error=f"Escalation failed: {str(e)}"
        ).model_dump_json(indent=2)


@function_tool
async def send_response(ticket_id: str, message: str, channel: str) -> str:
    """
    Send a response to a customer on the specified channel.

    Args:
        ticket_id: The ID of the ticket to respond to
        message: The response message to send
        channel: "email", "whatsapp", or "web_form"

    Returns:
        JSON string with success, ticket_id, message_id, channel, status, etc.
    """
    try:
        logger.info(f"Sending response to ticket {ticket_id} via {channel}")

        if not ticket_id or not ticket_id.strip():
            raise ValueError("ticket_id is required")
        if not message or not message.strip():
            raise ValueError("message is required")
        if channel not in ["email", "whatsapp", "web_form"]:
            raise ValueError("channel must be email, whatsapp, or web_form")

        if channel == "whatsapp" and len(message) > 300:
            logger.warning(f"WhatsApp message ({len(message)} chars) exceeds 300 char limit")
            message = message[:297] + "..."

        message_id = str(uuid.uuid4())
        delivered_at = datetime.now().isoformat()

        output = SendResponseOutput(
            success=True, ticket_id=ticket_id, message_id=message_id,
            channel=channel, status="delivered", delivered_at=delivered_at,
            message_length=len(message)
        )
        return output.model_dump_json(indent=2)

    except ValueError as e:
        return SendResponseOutput(
            success=False, ticket_id=ticket_id, message_id=None,
            channel=channel, status="failed", delivered_at="",
            message_length=len(message), error=str(e)
        ).model_dump_json(indent=2)
    except Exception as e:
        logger.error(f"Unexpected error in send_response: {e}", exc_info=True)
        return SendResponseOutput(
            success=False, ticket_id=ticket_id, message_id=None,
            channel=channel, status="failed", delivered_at="",
            message_length=len(message), error=f"Failed to send: {str(e)}"
        ).model_dump_json(indent=2)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def get_all_tool_names() -> list[str]:
    """Get list of all available tool names."""
    return ["search_knowledge_base", "create_ticket", "get_customer_history", 
            "escalate_to_human", "send_response"]


def get_tool_description(tool_name: str) -> str:
    """Get description for a specific tool."""
    descriptions = {
        "search_knowledge_base": "Search product documentation for relevant articles",
        "create_ticket": "Create a new support ticket",
        "get_customer_history": "Retrieve customer's full interaction history",
        "escalate_to_human": "Escalate ticket to human support",
        "send_response": "Send formatted response to customer"
    }
    return descriptions.get(tool_name, "Unknown tool")


# =============================================================================
# MAIN (Testing)
# =============================================================================

if __name__ == "__main__":
    """Test the production tools."""
    async def test_tools():
        print("=" * 80)
        print("NEXUSFLOW DIGITAL FTE - PRODUCTION TOOLS TEST")
        print("=" * 80)

        print("\n1. Testing search_knowledge_base...")
        result = await search_knowledge_base("how to export gantt chart")
        print(f"   Result: {result[:200]}...")

        print("\n2. Testing get_customer_history...")
        result = await get_customer_history("alice@techcorp.com")
        print(f"   Result: {result[:200]}...")

        print("\n3. Testing create_ticket...")
        result = await create_ticket(
            customer_id="test@example.com",
            issue="Test issue for production tools",
            priority="medium", channel="email"
        )
        print(f"   Result: {result[:200]}...")

        print("\n" + "=" * 80)
        print("TOOLS TEST COMPLETE")
        print("=" * 80)

    asyncio.run(test_tools())
