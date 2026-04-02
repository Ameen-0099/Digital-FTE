# Exercise 1.4: MCP Server Documentation

## Overview

This document describes the Model Context Protocol (MCP) server implementation for the NexusFlow Customer Success Digital FTE. The MCP server exposes the MemoryAgent functionality as standardized tools that can be consumed by AI agents, including OpenAI Custom Agents.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    MCP Client (e.g., Claude)                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ MCP Protocol (stdio)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   MCP Server (nexusflow-digital-fte)            │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Tool Router                            │  │
│  │  list_tools() / call_tool()                              │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────┐ │
│  │   search_   ││  create_    ││   get_      ││ escalate │ │
│  │ knowledge   ││  ticket     ││  customer   ││ _to_human│ │
│  │   _base     ││             ││  _history   ││          │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └──────────┘ │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐              │
│  │   send_     ││   analyze_  ││   extract_  │              │
│  │  response   ││  sentiment  ││   topics    │              │
│  └─────────────┘ └─────────────┘ └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MemoryAgent (Exercise 1.3)                   │
│  - Persistent conversation memory                               │
│  - Sentiment analysis                                           │
│  - Topic extraction                                             │
│  - Knowledge base search                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tool List and Purpose

### Required Tools (per Hackathon Specification)

| # | Tool Name | Purpose | Required Parameters |
|---|-----------|---------|---------------------|
| 1 | `search_knowledge_base` | Search product documentation | `query: str` |
| 2 | `create_ticket` | Create new support ticket | `customer_id, issue, priority, channel` |
| 3 | `get_customer_history` | Get customer's full interaction history | `customer_id: str` |
| 4 | `escalate_to_human` | Escalate ticket to human support | `ticket_id, reason` |
| 5 | `send_response` | Send response to customer | `ticket_id, message, channel` |

### Additional Tools (Bonus)

| # | Tool Name | Purpose | Required Parameters |
|---|-----------|---------|---------------------|
| 6 | `analyze_sentiment` | Analyze emotional state of message | `message: str` |
| 7 | `extract_topics` | Extract topics from message | `message: str` |

---

## Tool Definitions

### 1. search_knowledge_base

**Purpose:** Search the NexusFlow knowledge base for relevant documentation.

**When to use:**
- Finding product features and how-to guides
- Technical troubleshooting steps
- Billing and pricing information
- Integration setup instructions
- Compliance and security documentation

**Parameters:**
```json
{
  "query": {
    "type": "string",
    "description": "The search query - can be a question, keyword, or topic description",
    "examples": ["how to export gantt chart", "billing refund", "SSO setup"]
  }
}
```

**Response:**
```json
{
  "query": "export gantt chart to PDF",
  "results_count": 3,
  "articles": [
    {
      "key": "gantt_export",
      "title": "Exporting Gantt Charts",
      "content": "To export a Gantt chart to PDF: 1. Open your project...",
      "score": 7
    }
  ]
}
```

---

### 2. create_ticket

**Purpose:** Create a new support ticket in the NexusFlow system.

**When to use:**
- Customer reports a new issue
- Customer makes a feature request
- Customer has a billing inquiry
- Any customer interaction needs tracking

**Parameters:**
```json
{
  "customer_id": {
    "type": "string",
    "description": "Unique customer identifier (usually email address)"
  },
  "issue": {
    "type": "string",
    "description": "Description of the customer's issue or request"
  },
  "priority": {
    "type": "string",
    "enum": ["low", "medium", "high", "critical"]
  },
  "channel": {
    "type": "string",
    "enum": ["email", "whatsapp", "web_form"]
  },
  "subject": {
    "type": "string",
    "description": "Optional subject line for the ticket"
  }
}
```

**Response:**
```json
{
  "success": true,
  "ticket_id": "TKT-20260327-1CFA80F5",
  "customer_id": "alice@techcorp.com",
  "subject": "Gantt export issue",
  "priority": "high",
  "channel": "email",
  "status": "open",
  "created_at": "2026-03-27T23:01:24.065220",
  "conversation_id": "CONV-20260327-alice@te"
}
```

---

### 3. get_customer_history

**Purpose:** Retrieve complete customer interaction history across ALL channels.

**When to use:**
- Understanding customer's past issues and resolutions
- Seeing sentiment trends over time
- Checking if customer has had similar issues before
- Getting context before responding to returning customer
- Reviewing channel preferences and switch history

**Parameters:**
```json
{
  "customer_id": {
    "type": "string",
    "description": "Unique customer identifier (usually email address)"
  }
}
```

**Response:**
```json
{
  "customer_id": "history@test.com",
  "found": true,
  "name": "history",
  "email": "history@test.com",
  "company": "Unknown",
  "plan": "Unknown",
  "total_messages": 4,
  "topics_discussed": ["technical_issue"],
  "current_sentiment": "frustrated",
  "sentiment_trend": "stable",
  "channel_history": ["email", "email"],
  "last_interaction": "2026-03-27T23:01:24.093223",
  "status": "in_progress",
  "tickets": [
    {
      "ticket_id": "TKT-20260327-0DC4FDC7",
      "subject": "Support Request",
      "status": "open",
      "priority": "medium",
      "created_at": "2026-03-27T23:01:24.092222"
    }
  ]
}
```

---

### 4. escalate_to_human

**Purpose:** Escalate a ticket to human support when AI cannot resolve the issue.

**When to use:**
- Customer explicitly requests to speak with a human
- Issue requires specialist knowledge (billing disputes, legal, security)
- Customer is very frustrated or panicked (VIP treatment needed)
- Low confidence in AI-generated response
- Technical issue requires engineering team
- Legal, compliance, or security matters
- Enterprise contract or partnership inquiries

**Parameters:**
```json
{
  "ticket_id": {
    "type": "string",
    "description": "The ID of the ticket to escalate"
  },
  "reason": {
    "type": "string",
    "description": "Reason for escalation. Be specific."
  },
  "urgency": {
    "type": "string",
    "enum": ["normal", "high", "critical"]
  }
}
```

**Response:**
```json
{
  "success": true,
  "escalation_id": "ESC-20260327-37BC62",
  "ticket_id": "TKT-20260327-2067D72B",
  "escalation_level": "L1_Tier1",
  "urgency": "high",
  "status": "pending",
  "created_at": "2026-03-27T23:01:24.117221",
  "reason": "Billing dispute requires verification - customer charged twice"
}
```

**Escalation Levels (Automatic):**
| Level | Description | Trigger Keywords |
|-------|-------------|------------------|
| L1_Tier1 | General support agent | billing, refund, charge, human, person |
| L2_Tier2 | Technical specialist | technical, integration, api, advanced |
| L3_Tier3 | Senior engineer | security, breach, critical, vip |
| L4_Management | Executive/management | legal, lawsuit, attorney, court |

---

### 5. send_response

**Purpose:** Send a response to a customer on the specified channel.

**When to use:**
- Generated an answer to customer's question
- Providing troubleshooting steps
- Acknowledging receipt of message
- Following up on previous issue

**Parameters:**
```json
{
  "ticket_id": {
    "type": "string",
    "description": "The ID of the ticket to respond to"
  },
  "message": {
    "type": "string",
    "description": "The response message to send"
  },
  "channel": {
    "type": "string",
    "enum": ["email", "whatsapp", "web_form"]
  }
}
```

**Response:**
```json
{
  "success": true,
  "ticket_id": "TKT-20260327-54636AFD",
  "message_id": "87c81356-90c7-4fb1-8773-239aad7c9e85",
  "channel": "email",
  "status": "delivered",
  "delivered_at": "2026-03-27T23:01:24.140223",
  "message_length": 170
}
```

---

### 6. analyze_sentiment (Bonus)

**Purpose:** Analyze the sentiment of a customer message.

**When to use:**
- Detect frustration, anger, or panic early
- Identify very positive feedback
- Track sentiment changes during conversation
- Determine if de-escalation is needed

**Parameters:**
```json
{
  "message": {
    "type": "string",
    "description": "The customer message to analyze"
  }
}
```

**Response:**
```json
{
  "message_preview": "This is so frustrating! The export feature is broken...",
  "sentiment": "frustrated",
  "urgency": "high",
  "analyzed_at": "2026-03-27T23:01:24.150223"
}
```

---

### 7. extract_topics (Bonus)

**Purpose:** Extract topics from a customer message for categorization.

**When to use:**
- Automatically categorize incoming messages
- Route tickets to appropriate teams
- Track common issue types for reporting
- Identify trending topics

**Parameters:**
```json
{
  "message": {
    "type": "string",
    "description": "The customer message to extract topics from"
  }
}
```

**Response:**
```json
{
  "message_preview": "How do I set up recurring tasks and track time...",
  "topics": ["recurring_tasks", "guest_access", "time_tracking"],
  "topics_count": 3,
  "extracted_at": "2026-03-27T23:01:24.163224"
}
```

---

## Test Results

### Test Suite Summary

| Tool | Test Status | Notes |
|------|-------------|-------|
| search_knowledge_base | ✅ PASS | 3/3 searches returned relevant results |
| create_ticket | ✅ PASS | All channels (email, whatsapp, web_form) working |
| get_customer_history | ✅ PASS | History retrieval and not-found cases working |
| escalate_to_human | ✅ PASS | Escalation levels correctly assigned |
| send_response | ✅ PASS | Multi-channel response delivery working |
| analyze_sentiment | ✅ PASS | All sentiment categories detected correctly |
| extract_topics | ✅ PASS | Topic extraction working for single and multiple topics |

**Overall: 7/7 tools passed (100%)**

### Test Data Summary

After running tests:
- **Total tickets created:** 7
- **Total escalations:** 2
- **Channels tested:** email, whatsapp, web_form
- **Priority levels tested:** low, medium, high, critical

### Sample Test Output

```
================================================================================
TEST SUMMARY REPORT
================================================================================
   ✅ PASS: search_knowledge_base
   ✅ PASS: create_ticket
   ✅ PASS: get_customer_history
   ✅ PASS: escalate_to_human
   ✅ PASS: send_response
   ✅ PASS: analyze_sentiment
   ✅ PASS: extract_topics

   Total: 7/7 tools passed (100%)
```

---

## Running the MCP Server

### Prerequisites

```bash
# Ensure MCP SDK is installed
pip install mcp

# Ensure project dependencies are installed
pip install -r requirements.txt
```

### Starting the Server

```bash
# From project root
python src/mcp_server.py
```

### Server Output

```
================================================================================
NEXUSFLOW DIGITAL FTE - MCP SERVER
Exercise 1.4: Model Context Protocol Server
================================================================================

Starting MCP server 'nexusflow-digital-fte'...
Available tools:
  - search_knowledge_base
  - create_ticket
  - get_customer_history
  - escalate_to_human
  - send_response
  - analyze_sentiment
  - extract_topics

Server running on stdio transport...
================================================================================
```

### Running Tests

```bash
# From project root
python src/test_mcp_tools.py
```

---

## Production Usage (OpenAI @function_tool)

### Integration with OpenAI Agents

The MCP server is designed to be used with OpenAI's Custom Agent framework via the `@function_tool` decorator.

#### Example Integration

```python
from openai import Agent
from openai.agents import function_tool

# Create MCP client connection
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

@function_tool
async def search_knowledge_base(query: str) -> dict:
    """Search NexusFlow knowledge base."""
    async with stdio_client(server_parameters) as (read, write):
        async with ClientSession(read, write) as session:
            result = await session.call_tool("search_knowledge_base", {"query": query})
            return json.loads(result.content[0].text)

@function_tool
async def create_ticket(customer_id: str, issue: str, priority: str, channel: str) -> dict:
    """Create support ticket."""
    async with stdio_client(server_parameters) as (read, write):
        async with ClientSession(read, write) as session:
            result = await session.call_tool("create_ticket", {
                "customer_id": customer_id,
                "issue": issue,
                "priority": priority,
                "channel": channel
            })
            return json.loads(result.content[0].text)

# ... define other tools similarly

# Create agent with tools
agent = Agent(
    name="NexusFlow Support Agent",
    instructions="You are a helpful customer support agent for NexusFlow.",
    tools=[
        search_knowledge_base,
        create_ticket,
        get_customer_history,
        escalate_to_human,
        send_response,
        analyze_sentiment,
        extract_topics
    ]
)
```

### Tool Calling Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   OpenAI Agent  │────▶│  MCP Client     │────▶│  MCP Server     │
│   (GPT-4/5)     │     │  (stdio)        │     │  (nexusflow)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │                       │
        │  1. User message      │                       │
        │──────────────────────▶│                       │
        │                       │  2. Tool call request │
        │                       │──────────────────────▶│
        │                       │                       │
        │                       │  3. Process with      │
        │                       │     MemoryAgent       │
        │                       │◀──────────────────────│
        │  4. Tool result       │                       │
        │◀──────────────────────│                       │
        │                       │                       │
        │  5. Generate response │                       │
        │◀──────────────────────│                       │
        │                       │                       │
```

---

## Files Created

| File | Purpose |
|------|---------|
| `src/mcp_server.py` | Main MCP server implementation (924 lines) |
| `src/test_mcp_tools.py` | Comprehensive tool test suite (426 lines) |
| `specs/mcp-server.md` | This documentation file |

---

## Current Limitations

### 1. In-Memory Storage

| Limitation | Impact | Production Solution |
|------------|--------|---------------------|
| Tickets stored in dict | Lost on server restart | PostgreSQL database |
| Escalations in memory | No persistence | PostgreSQL with transactions |
| No data replication | Single point of failure | Database replication |

### 2. Transport Limitations

| Limitation | Impact | Production Solution |
|------------|--------|---------------------|
| stdio only | Local execution only | SSE/WebSocket transport |
| No authentication | Open access | API key / OAuth2 |
| No rate limiting | Potential abuse | Rate limiting middleware |

### 3. Integration Limitations

| Limitation | Impact | Production Solution |
|------------|--------|---------------------|
| No actual email sending | Simulated delivery | SendGrid / SES integration |
| No actual WhatsApp | Simulated delivery | WhatsApp Business API |
| No actual web form | Simulated delivery | Webhook integration |

---

## Production Improvements

### PostgreSQL Integration

```python
# Replace in-memory dict with database
async def handle_create_ticket_db(arguments: Dict[str, Any]) -> CallToolResult:
    async with db.get_cursor() as cur:
        await cur.execute("""
            INSERT INTO tickets (customer_id, issue, priority, channel, subject)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING ticket_id
        """, (customer_id, issue, priority, channel, subject))
        result = await cur.fetchone()
        return {"ticket_id": result['ticket_id']}
```

### Authentication

```python
from mcp.server.auth import AuthProvider

class NexusFlowAuth(AuthProvider):
    async def authenticate(self, token: str) -> bool:
        # Validate API key or JWT
        return await validate_token(token)

server = Server("nexusflow-digital-fte", auth=NexusFlowAuth())
```

### Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@server.call_tool()
@limiter.limit("100/minute")
async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
    # ... existing implementation
```

---

## Next Steps

1. **PostgreSQL Integration** - Replace in-memory storage with database
2. **SSE Transport** - Enable remote server connections
3. **Authentication** - Add API key / OAuth2 security
4. **Email Integration** - Connect to SendGrid/SES for actual email sending
5. **WhatsApp Integration** - Connect to WhatsApp Business API
6. **Monitoring** - Add logging and metrics collection
7. **Error Handling** - Improve error responses and retry logic

---

## Conclusion

The MCP server successfully implements:

✅ **5 required tools** (search_knowledge_base, create_ticket, get_customer_history, escalate_to_human, send_response)
✅ **2 bonus tools** (analyze_sentiment, extract_topics)
✅ **Proper MCP structure** (list_tools, call_tool, server.run())
✅ **Comprehensive docstrings** for LLM consumption
✅ **Channel enum** (EMAIL, WHATSAPP, WEB_FORM)
✅ **Integration with MemoryAgent** (reuses existing code)
✅ **100% test pass rate** (7/7 tools)

**Test Results: 7/7 tools passing (100%)**

This MCP server is ready for integration with OpenAI Custom Agents and provides a solid foundation for production deployment.
