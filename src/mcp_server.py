"""
NexusFlow Customer Success Digital FTE - MCP Server
====================================================
Exercise 1.4 - Build the MCP Server

This module exposes the MemoryAgent as a Model Context Protocol (MCP) server,
enabling it to be used as a tool by AI agents (e.g., OpenAI Custom Agent).

The server provides tools for:
- Knowledge base search
- Ticket creation and management
- Customer history retrieval
- Escalation to human support
- Response sending across channels

Author: Digital FTE Team
Version: 1.0.0 (Exercise 1.4)
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

# MCP SDK imports
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    CallToolResult,
)

# Import MemoryAgent from our existing implementation
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "agent"))

from memory_agent import MemoryAgent
from core_loop import Channel, KnowledgeBase


# =============================================================================
# CHANNEL ENUM (MCP Tool Parameter Type)
# =============================================================================

class MCPChannel(str, Enum):
    """
    Supported communication channels for the MCP server.
    
    These values are used when creating tickets or sending responses
    to specify the communication channel.
    """
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    WEB_FORM = "web_form"


# =============================================================================
# MCP SERVER INITIALIZATION
# =============================================================================

# Create the MCP server instance
server = Server("nexusflow-digital-fte")

# Initialize the MemoryAgent (shared instance for all tools)
memory_agent = MemoryAgent(storage_path="data/conversations")

# Initialize the KnowledgeBase (for search tool)
knowledge_base = KnowledgeBase()

# In-memory escalation store (in production, this would be in PostgreSQL)
escalations: Dict[str, Dict[str, Any]] = {}

# In-memory ticket store (in production, this would be in PostgreSQL)
tickets: Dict[str, Dict[str, Any]] = {}


# =============================================================================
# MCP TOOL DEFINITIONS
# =============================================================================

@server.list_tools()
async def list_tools() -> List[Tool]:
    """
    List all available MCP tools.
    
    This function is called by the MCP client to discover what tools
    are available. Each tool includes a name, description, and schema
    for its input parameters.
    
    Returns:
        List of Tool definitions with names, descriptions, and JSON schemas
    """
    return [
        Tool(
            name="search_knowledge_base",
            description="""Search the NexusFlow knowledge base for relevant documentation.
            
            Use this tool when you need to find information about:
            - Product features and how-to guides
            - Technical troubleshooting steps
            - Billing and pricing information
            - Integration setup instructions
            - Compliance and security documentation
            
            The search returns up to 3 relevant articles with titles, content, and relevance scores.
            Higher scores indicate more relevant results.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query - can be a question, keyword, or topic description. Examples: 'how to export gantt chart', 'billing refund', 'SSO setup'"
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="create_ticket",
            description="""Create a new support ticket in the NexusFlow system.
            
            Use this tool when:
            - A customer reports a new issue
            - A customer makes a feature request
            - A customer has a billing inquiry
            - Any customer interaction needs to be tracked
            
            The ticket is automatically assigned a unique ID and timestamp.
            The customer must already exist in the system (identified by customer_id).
            
            Priority levels:
            - low: Non-urgent requests (feature requests, general inquiries)
            - medium: Standard support requests (how-to questions)
            - high: Urgent issues (technical problems affecting work)
            - critical: Blocking issues (entire organization cannot work)
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "Unique customer identifier (usually email address). Examples: 'john@company.com', 'jane@startup.io'"
                    },
                    "issue": {
                        "type": "string",
                        "description": "Description of the customer's issue or request. Should be clear and specific."
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "description": "Priority level based on urgency and impact"
                    },
                    "channel": {
                        "type": "string",
                        "enum": ["email", "whatsapp", "web_form"],
                        "description": "Channel through which the customer contacted support"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Optional subject line for the ticket"
                    }
                },
                "required": ["customer_id", "issue", "priority", "channel"]
            }
        ),
        Tool(
            name="get_customer_history",
            description="""Retrieve complete customer interaction history across ALL channels.
            
            Use this tool when you need to:
            - Understand the customer's past issues and resolutions
            - See sentiment trends over time
            - Check if customer has had similar issues before
            - Get context before responding to a returning customer
            - Review channel preferences and switch history
            
            This returns comprehensive history including:
            - All past conversations and messages
            - Topics previously discussed
            - Sentiment progression (improving/declining/stable)
            - Channel switches (e.g., started on email, moved to WhatsApp)
            - Current ticket status
            
            The customer_id is typically their email address for easy lookup.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "customer_id": {
                        "type": "string",
                        "description": "Unique customer identifier (usually email address). Examples: 'john@company.com', 'jane@startup.io'"
                    }
                },
                "required": ["customer_id"]
            }
        ),
        Tool(
            name="escalate_to_human",
            description="""Escalate a ticket to human support when AI cannot resolve the issue.
            
            Use this tool when:
            - Customer explicitly requests to speak with a human
            - Issue requires specialist knowledge (billing disputes, legal, security)
            - Customer is very frustrated or panicked (VIP treatment needed)
            - Low confidence in AI-generated response
            - Technical issue requires engineering team
            - Legal, compliance, or security matters
            - Enterprise contract or partnership inquiries

            Escalation levels (automatic based on reason):
            - L1_Tier1: General support agent (billing verification, basic requests)
            - L2_Tier2: Technical specialist (integrations, advanced features)
            - L3_Tier3: Senior engineer (critical technical issues, VIP customers)
            - L4_Management: Executive/management (legal, partnerships, escalations)

            The escalation includes full conversation context for seamless handoff.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_id": {
                        "type": "string",
                        "description": "The ID of the ticket to escalate. Examples: 'TKT-20260327-001', 'TKT-20260328-015'"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Reason for escalation. Be specific: 'Customer requested human agent', 'Billing dispute requires verification', 'VIP customer very frustrated', 'Legal matter - GDPR request'"
                    },
                    "urgency": {
                        "type": "string",
                        "enum": ["normal", "high", "critical"],
                        "description": "How quickly human attention is needed"
                    }
                },
                "required": ["ticket_id", "reason"]
            }
        ),
        Tool(
            name="send_response",
            description="""Send a response to a customer on the specified channel.
            
            Use this tool when:
            - You have generated an answer to the customer's question
            - You need to provide troubleshooting steps
            - You want to acknowledge receipt of their message
            - You are following up on a previous issue
            
            The response is automatically:
            - Formatted appropriately for the channel (email=formal, WhatsApp=concise)
            - Added to the conversation history
            - Linked to the ticket for tracking
            
            Channel-specific formatting:
            - email: Full sentences, professional tone, signature included
            - whatsapp: Concise, emoji-friendly, under 300 chars
            - web_form: Professional but conversational, moderate length
            
            Always ensure the response addresses the customer's actual question.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_id": {
                        "type": "string",
                        "description": "The ID of the ticket to respond to"
                    },
                    "message": {
                        "type": "string",
                        "description": "The response message to send to the customer. Should be helpful, accurate, and appropriate for the channel."
                    },
                    "channel": {
                        "type": "string",
                        "enum": ["email", "whatsapp", "web_form"],
                        "description": "Channel to send the response on"
                    }
                },
                "required": ["ticket_id", "message", "channel"]
            }
        ),
        # Additional helpful tools
        Tool(
            name="analyze_sentiment",
            description="""Analyze the sentiment of a customer message.
            
            Use this tool to understand the customer's emotional state:
            - Detect frustration, anger, or panic early
            - Identify very positive feedback for the team
            - Track sentiment changes during a conversation
            - Determine if de-escalation is needed
            
            Sentiment categories:
            - very_positive: Customer loves the product/service
            - positive: Customer is happy/satisfied
            - neutral: Customer is asking routine questions
            - concerned: Customer has worries or doubts
            - frustrated: Customer is annoyed
            - very_frustrated: Customer is quite upset
            - panicked: Customer is in crisis mode
            - angry: Customer is mad
            
            Returns sentiment label, urgency level, and confidence score.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The customer message to analyze"
                    }
                },
                "required": ["message"]
            }
        ),
        Tool(
            name="extract_topics",
            description="""Extract topics from a customer message for categorization.
            
            Use this tool to:
            - Automatically categorize incoming messages
            - Route tickets to appropriate teams
            - Track common issue types for reporting
            - Identify trending topics
            
            Topic categories include:
            - pricing, billing, export, integration, sso
            - mobile, recurring_tasks, guest_access, time_tracking
            - data_loss, performance, feature_request, technical_issue
            - onboarding, compliance, training
            
            Returns list of relevant topics found in the message.
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The customer message to extract topics from"
                    }
                },
                "required": ["message"]
            }
        )
    ]


# =============================================================================
# MCP TOOL HANDLERS
# =============================================================================

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    """
    Handle tool execution requests from MCP clients.
    
    This function routes tool calls to the appropriate handler based on
    the tool name. Each handler processes the arguments and returns
    structured results.
    
    Args:
        name: The name of the tool to call
        arguments: Dictionary of arguments for the tool
        
    Returns:
        CallToolResult with structured content (JSON) and optional error info
    """
    try:
        if name == "search_knowledge_base":
            return await handle_search_knowledge_base(arguments)
        elif name == "create_ticket":
            return await handle_create_ticket(arguments)
        elif name == "get_customer_history":
            return await handle_get_customer_history(arguments)
        elif name == "escalate_to_human":
            return await handle_escalate_to_human(arguments)
        elif name == "send_response":
            return await handle_send_response(arguments)
        elif name == "analyze_sentiment":
            return await handle_analyze_sentiment(arguments)
        elif name == "extract_topics":
            return await handle_extract_topics(arguments)
        else:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                isError=True
            )
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error executing {name}: {str(e)}")],
            isError=True
        )


# -----------------------------------------------------------------------------
# Tool Handler: search_knowledge_base
# -----------------------------------------------------------------------------

async def handle_search_knowledge_base(arguments: Dict[str, Any]) -> CallToolResult:
    """
    Handle search_knowledge_base tool execution.
    
    Searches the knowledge base for articles matching the query.
    Uses keyword matching and scoring to rank results.
    
    Args:
        arguments: Dictionary containing 'query' string
        
    Returns:
        CallToolResult with list of matching articles (title, content, score)
    """
    query = arguments.get("query", "")
    
    if not query:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: Query is required")],
            isError=True
        )
    
    # Search knowledge base
    results = knowledge_base.search(query)
    
    if not results:
        return CallToolResult(
            content=[TextContent(
                type="text", 
                text=json.dumps({
                    "query": query,
                    "results_count": 0,
                    "articles": [],
                    "message": "No relevant articles found"
                }, indent=2)
            )]
        )
    
    # Format results
    formatted_results = []
    for article in results:
        formatted_results.append({
            "key": article["key"],
            "title": article["title"],
            "content": article["content"],
            "score": article["score"]
        })
    
    response_data = {
        "query": query,
        "results_count": len(formatted_results),
        "articles": formatted_results
    }
    
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(response_data, indent=2))]
    )


# -----------------------------------------------------------------------------
# Tool Handler: create_ticket
# -----------------------------------------------------------------------------

async def handle_create_ticket(arguments: Dict[str, Any]) -> CallToolResult:
    """
    Handle create_ticket tool execution.
    
    Creates a new support ticket and stores it in memory.
    In production, this would write to PostgreSQL.
    
    Args:
        arguments: Dictionary containing customer_id, issue, priority, channel, subject
        
    Returns:
        CallToolResult with ticket_id and confirmation
    """
    customer_id = arguments.get("customer_id")
    issue = arguments.get("issue")
    priority = arguments.get("priority", "medium")
    channel = arguments.get("channel", "email")
    subject = arguments.get("subject", "Support Request")
    
    # Validate required fields
    if not customer_id or not issue:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: customer_id and issue are required")],
            isError=True
        )
    
    # Validate channel
    if channel not in ["email", "whatsapp", "web_form"]:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: Invalid channel '{channel}'. Must be email, whatsapp, or web_form")],
            isError=True
        )
    
    # Validate priority
    if priority not in ["low", "medium", "high", "critical"]:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: Invalid priority '{priority}'. Must be low, medium, high, or critical")],
            isError=True
        )
    
    # Generate ticket ID
    ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    
    # Create ticket record
    ticket = {
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "subject": subject,
        "issue": issue,
        "priority": priority,
        "channel": channel,
        "status": "open",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "messages": [],
        "escalation_level": None
    }
    
    # Store ticket
    tickets[ticket_id] = ticket
    
    # Also create in memory agent for persistence
    from core_loop import CustomerProfile
    customer = CustomerProfile(
        name=customer_id.split("@")[0],  # Extract name from email
        email=customer_id if "@" in customer_id else None,
        company="Unknown",
        plan="Unknown"
    )
    
    # Process through memory agent to create conversation record
    memory_result = memory_agent.process_message(
        message=issue,
        channel=channel,
        customer=customer,
        subject=subject
    )
    
    response_data = {
        "success": True,
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "subject": subject,
        "priority": priority,
        "channel": channel,
        "status": "open",
        "created_at": ticket["created_at"],
        "conversation_id": memory_result["metadata"]["conversation_id"]
    }
    
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(response_data, indent=2))]
    )


# -----------------------------------------------------------------------------
# Tool Handler: get_customer_history
# -----------------------------------------------------------------------------

async def handle_get_customer_history(arguments: Dict[str, Any]) -> CallToolResult:
    """
    Handle get_customer_history tool execution.
    
    Retrieves complete customer history from the MemoryAgent.
    Includes all conversations, topics, sentiment trends, and channel history.
    
    Args:
        arguments: Dictionary containing customer_id
        
    Returns:
        CallToolResult with comprehensive customer history
    """
    customer_id = arguments.get("customer_id")
    
    if not customer_id:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: customer_id is required")],
            isError=True
        )
    
    # Get history from memory agent
    history = memory_agent.get_customer_summary(customer_id)
    
    if not history:
        return CallToolResult(
            content=[TextContent(
                type="text",
                text=json.dumps({
                    "customer_id": customer_id,
                    "found": False,
                    "message": "No history found for this customer"
                }, indent=2)
            )]
        )
    
    # Get all tickets for this customer
    customer_tickets = [
        t for t in tickets.values() 
        if t["customer_id"] == customer_id
    ]
    
    response_data = {
        "customer_id": customer_id,
        "found": True,
        "name": history.get("name", "Unknown"),
        "email": history.get("email", customer_id),
        "company": history.get("company", "Unknown"),
        "plan": history.get("plan", "Unknown"),
        "total_messages": history.get("total_messages", 0),
        "topics_discussed": history.get("topics_discussed", []),
        "current_sentiment": history.get("current_sentiment", "unknown"),
        "sentiment_trend": history.get("sentiment_trend", "stable"),
        "channel_history": history.get("channel_history", []),
        "last_interaction": history.get("last_interaction", "never"),
        "status": history.get("status", "unknown"),
        "tickets": [
            {
                "ticket_id": t["ticket_id"],
                "subject": t["subject"],
                "status": t["status"],
                "priority": t["priority"],
                "created_at": t["created_at"]
            }
            for t in customer_tickets
        ]
    }
    
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(response_data, indent=2))]
    )


# -----------------------------------------------------------------------------
# Tool Handler: escalate_to_human
# -----------------------------------------------------------------------------

async def handle_escalate_to_human(arguments: Dict[str, Any]) -> CallToolResult:
    """
    Handle escalate_to_human tool execution.
    
    Creates an escalation record for human handoff.
    Determines escalation level based on reason.
    
    Args:
        arguments: Dictionary containing ticket_id, reason, urgency
        
    Returns:
        CallToolResult with escalation_id and level
    """
    ticket_id = arguments.get("ticket_id")
    reason = arguments.get("reason")
    urgency = arguments.get("urgency", "normal")
    
    # Validate required fields
    if not ticket_id or not reason:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: ticket_id and reason are required")],
            isError=True
        )
    
    # Check if ticket exists
    if ticket_id not in tickets:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: Ticket '{ticket_id}' not found")],
            isError=True
        )
    
    # Determine escalation level based on reason
    escalation_level = "L1_Tier1"  # Default
    
    reason_lower = reason.lower()
    if any(word in reason_lower for word in ["legal", "lawsuit", "attorney", "court"]):
        escalation_level = "L4_Management"
    elif any(word in reason_lower for word in ["security", "breach", "critical", "vip"]):
        escalation_level = "L3_Tier3"
    elif any(word in reason_lower for word in ["technical", "integration", "api", "advanced"]):
        escalation_level = "L2_Tier2"
    elif any(word in reason_lower for word in ["billing", "refund", "charge", "human", "person"]):
        escalation_level = "L1_Tier1"
    
    # Generate escalation ID
    escalation_id = f"ESC-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
    
    # Create escalation record
    escalation = {
        "escalation_id": escalation_id,
        "ticket_id": ticket_id,
        "reason": reason,
        "urgency": urgency,
        "escalation_level": escalation_level,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "assigned_to": None
    }
    
    # Store escalation
    escalations[escalation_id] = escalation
    
    # Update ticket
    tickets[ticket_id]["escalation_level"] = escalation_level
    tickets[ticket_id]["status"] = "escalated"
    
    response_data = {
        "success": True,
        "escalation_id": escalation_id,
        "ticket_id": ticket_id,
        "escalation_level": escalation_level,
        "urgency": urgency,
        "status": "pending",
        "created_at": escalation["created_at"],
        "reason": reason
    }
    
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(response_data, indent=2))]
    )


# -----------------------------------------------------------------------------
# Tool Handler: send_response
# -----------------------------------------------------------------------------

async def handle_send_response(arguments: Dict[str, Any]) -> CallToolResult:
    """
    Handle send_response tool execution.
    
    Sends a response to the customer and records it in the ticket.
    In production, this would actually send via email/WhatsApp API.
    
    Args:
        arguments: Dictionary containing ticket_id, message, channel
        
    Returns:
        CallToolResult with delivery status
    """
    ticket_id = arguments.get("ticket_id")
    message = arguments.get("message")
    channel = arguments.get("channel", "email")
    
    # Validate required fields
    if not ticket_id or not message:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: ticket_id and message are required")],
            isError=True
        )
    
    # Check if ticket exists
    if ticket_id not in tickets:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: Ticket '{ticket_id}' not found")],
            isError=True
        )
    
    # Validate channel
    if channel not in ["email", "whatsapp", "web_form"]:
        return CallToolResult(
            content=[TextContent(type="text", text=f"Error: Invalid channel '{channel}'. Must be email, whatsapp, or web_form")],
            isError=True
        )
    
    # Create message record
    message_record = {
        "id": str(uuid.uuid4()),
        "direction": "outbound",
        "content": message,
        "channel": channel,
        "sent_at": datetime.now().isoformat(),
        "status": "sent"
    }
    
    # Add to ticket
    tickets[ticket_id]["messages"].append(message_record)
    tickets[ticket_id]["updated_at"] = datetime.now().isoformat()
    
    # Simulate delivery (in production, would call actual APIs)
    delivery_status = "delivered"
    delivery_time = datetime.now().isoformat()
    
    response_data = {
        "success": True,
        "ticket_id": ticket_id,
        "message_id": message_record["id"],
        "channel": channel,
        "status": delivery_status,
        "delivered_at": delivery_time,
        "message_length": len(message)
    }
    
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(response_data, indent=2))]
    )


# -----------------------------------------------------------------------------
# Tool Handler: analyze_sentiment
# -----------------------------------------------------------------------------

async def handle_analyze_sentiment(arguments: Dict[str, Any]) -> CallToolResult:
    """
    Handle analyze_sentiment tool execution.
    
    Uses the SentimentAnalyzer to determine emotional state of a message.
    
    Args:
        arguments: Dictionary containing message
        
    Returns:
        CallToolResult with sentiment, urgency, and confidence
    """
    message = arguments.get("message")
    
    if not message:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: message is required")],
            isError=True
        )
    
    # Use existing sentiment analyzer
    sentiment, urgency = memory_agent.sentiment_analyzer.analyze(message)
    
    response_data = {
        "message_preview": message[:100] + "..." if len(message) > 100 else message,
        "sentiment": sentiment.value,
        "urgency": urgency.value,
        "analyzed_at": datetime.now().isoformat()
    }
    
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(response_data, indent=2))]
    )


# -----------------------------------------------------------------------------
# Tool Handler: extract_topics
# -----------------------------------------------------------------------------

async def handle_extract_topics(arguments: Dict[str, Any]) -> CallToolResult:
    """
    Handle extract_topics tool execution.
    
    Uses the TopicExtractor to identify topics in a message.
    
    Args:
        arguments: Dictionary containing message
        
    Returns:
        CallToolResult with list of topics
    """
    message = arguments.get("message")
    
    if not message:
        return CallToolResult(
            content=[TextContent(type="text", text="Error: message is required")],
            isError=True
        )
    
    # Use existing topic extractor
    topics = memory_agent.topic_extractor.extract_topics(message)
    
    response_data = {
        "message_preview": message[:100] + "..." if len(message) > 100 else message,
        "topics": topics,
        "topics_count": len(topics),
        "extracted_at": datetime.now().isoformat()
    }
    
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(response_data, indent=2))]
    )


# =============================================================================
# SERVER ENTRY POINT
# =============================================================================

async def main():
    """
    Main entry point for the MCP server.
    
    Runs the server using stdio transport, which communicates via
    standard input/output. This is the standard way to run MCP servers
    for local development and production use.
    """
    # Run the server with stdio transport
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


def run():
    """
    Synchronous wrapper to run the MCP server.
    
    This function is called when the module is executed directly.
    It starts the asyncio event loop and runs the main server.
    """
    print("=" * 80)
    print("NEXUSFLOW DIGITAL FTE - MCP SERVER")
    print("Exercise 1.4: Model Context Protocol Server")
    print("=" * 80)
    print(f"\nStarting MCP server 'nexusflow-digital-fte'...")
    print(f"Available tools:")
    print(f"  - search_knowledge_base")
    print(f"  - create_ticket")
    print(f"  - get_customer_history")
    print(f"  - escalate_to_human")
    print(f"  - send_response")
    print(f"  - analyze_sentiment")
    print(f"  - extract_topics")
    print(f"\nServer running on stdio transport...")
    print("=" * 80)
    
    asyncio.run(main())


if __name__ == "__main__":
    run()
