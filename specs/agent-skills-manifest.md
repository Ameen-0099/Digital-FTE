# Agent Skills Manifest

**NexusFlow Customer Success Digital FTE**  
**Exercise 1.5: Define Agent Skills**

| Document Info | Details |
|---------------|---------|
| Version | 1.0.0 |
| Author | Digital FTE Team |
| Created | 2026-03-27 |
| Status | Production Ready |
| Related | Exercise 1.4 (MCP Server), Exercise 1.3 (Memory) |

---

## Table of Contents

1. [Overview](#overview)
2. [Skills Usage Workflow](#skills-usage-workflow)
3. [Skill 1: Knowledge Retrieval](#skill-1-knowledge-retrieval)
4. [Skill 2: Sentiment Analysis](#skill-2-sentiment-analysis)
5. [Skill 3: Escalation Decision](#skill-3-escalation-decision)
6. [Skill 4: Channel Adaptation](#skill-4-channel-adaptation)
7. [Skill 5: Customer Identification](#skill-5-customer-identification)
8. [Example Interaction Flows](#example-interaction-flows)
9. [MCP Tool Mapping](#mcp-tool-mapping)

---

## Overview

This manifest defines the core reusable skills that compose the NexusFlow Customer Success Digital FTE agent. Each skill is a self-contained capability that can be:

- **Composed** into larger workflows
- **Tested** independently
- **Reused** across different agent configurations
- **Converted** to `@function_tool` decorators for OpenAI Agents

### Skill Design Principles

1. **Single Responsibility** - Each skill does one thing well
2. **Stateless** - Skills don't maintain internal state (state is in MemoryAgent)
3. **Composable** - Skills can be chained together
4. **Testable** - Clear inputs/outputs enable unit testing
5. **Documented** - Clear contracts for LLM consumption

---

## Skills Usage Workflow

The agent processes each customer interaction through skills in the following order:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CUSTOMER MESSAGE RECEIVED                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 1: Customer Identification Skill                                  │
│  ─────────────────────────────────                                      │
│  Purpose: Identify who is contacting us                                 │
│  Input: email, phone, or other identifiers from message metadata        │
│  Output: customer_id, customer profile, conversation history            │
│                                                                         │
│  MCP Tool: get_customer_history(customer_id)                            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 2: Sentiment Analysis Skill                                       │
│  ───────────────────────────────                                        │
│  Purpose: Understand customer's emotional state                         │
│  Input: message text                                                    │
│  Output: sentiment label, urgency, confidence score                     │
│                                                                         │
│  MCP Tool: analyze_sentiment(message)                                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 3: Knowledge Retrieval Skill                                      │
│  ───────────────────────────────                                        │
│  Purpose: Find relevant information to answer the question              │
│  Input: message content (the question/issue)                            │
│  Output: relevant articles, relevance scores, confidence                │
│                                                                         │
│  MCP Tool: search_knowledge_base(query)                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 4: Generate Response (Internal)                                   │
│  ─────────────────────────────────                                      │
│  Purpose: Create appropriate response using knowledge + context         │
│  Input: knowledge results, customer context, sentiment                  │
│  Output: draft response text                                            │
│                                                                         │
│  Note: This is internal logic, not a separate skill                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 5: Escalation Decision Skill                                      │
│  ───────────────────────────────                                        │
│  Purpose: Determine if human intervention is needed                     │
│  Input: conversation context, sentiment, response confidence, category  │
│  Output: should_escalate (bool), reason, escalation_level               │
│                                                                         │
│  MCP Tool: escalate_to_human(ticket_id, reason) [if needed]             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 6: Channel Adaptation Skill                                       │
│  ───────────────────────────────                                        │
│  Purpose: Format response for the target channel                        │
│  Input: draft response, target channel (email/whatsapp/web_form)        │
│  Output: formatted response appropriate for channel                     │
│                                                                         │
│  MCP Tool: send_response(ticket_id, message, channel)                   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    RESPONSE SENT TO CUSTOMER                            │
└─────────────────────────────────────────────────────────────────────────┘
```

### Quick Reference

| Step | Skill | MCP Tool | Trigger |
|------|-------|----------|---------|
| 1 | Customer Identification | `get_customer_history` | Every incoming message |
| 2 | Sentiment Analysis | `analyze_sentiment` | Every incoming message |
| 3 | Knowledge Retrieval | `search_knowledge_base` | When customer asks question |
| 4 | (Response Generation) | (Internal) | After knowledge retrieval |
| 5 | Escalation Decision | `escalate_to_human` | After generating response |
| 6 | Channel Adaptation | `send_response` | Before sending response |

---

## Skill 1: Knowledge Retrieval

### Overview

Retrieves relevant documentation from the NexusFlow knowledge base to answer customer questions accurately.

### When to Use

| Scenario | Use This Skill? |
|----------|-----------------|
| Customer asks "how do I..." question | ✅ Yes |
| Customer reports technical issue | ✅ Yes |
| Customer asks about pricing/plans | ✅ Yes |
| Customer asks about features | ✅ Yes |
| Customer makes feature request | ❌ No (no KB article exists) |
| Customer requests billing refund | ❌ No (requires human) |
| Customer is panicked/emergency | ⚠️ Optional (escalate first) |

### Inputs

```python
{
    "query": {
        "type": "str",
        "description": "The search query derived from customer message",
        "required": True,
        "examples": [
            "how to export gantt chart to PDF",
            "set up recurring tasks",
            "billing refund duplicate charge",
            "SSO SAML configuration"
        ]
    }
}
```

### Outputs

```python
{
    "query": "str - Original search query",
    "results_count": "int - Number of articles found",
    "articles": [
        {
            "key": "str - Article identifier",
            "title": "str - Article title",
            "content": "str - Article content",
            "score": "float - Relevance score (higher = more relevant)"
        }
    ],
    "confidence": "float - Overall confidence in results (0.0-1.0)",
    "has_relevant_result": "bool - Whether any article scores above threshold"
}
```

### Implementation Notes

```python
async def knowledge_retrieval_skill(query: str) -> dict:
    """
    Retrieve relevant knowledge base articles for a customer query.
    
    Args:
        query: Search query derived from customer message
        
    Returns:
        Dictionary with articles and relevance metadata
    """
    # Call MCP tool
    result = await mcp_client.call_tool("search_knowledge_base", {"query": query})
    data = json.loads(result.content[0].text)
    
    # Calculate confidence
    if data["results_count"] == 0:
        confidence = 0.0
    else:
        top_score = data["articles"][0]["score"]
        confidence = min(1.0, top_score / 10.0)  # Normalize to 0-1
    
    return {
        **data,
        "confidence": confidence,
        "has_relevant_result": confidence > 0.5
    }
```

### Thresholds

| Metric | Threshold | Action |
|--------|-----------|--------|
| `confidence > 0.7` | High confidence | Use top article for response |
| `confidence 0.4-0.7` | Medium confidence | Use articles with disclaimer |
| `confidence < 0.4` | Low confidence | Consider escalation |

### Related MCP Tool

```python
search_knowledge_base(query: str) → dict
```

---

## Skill 2: Sentiment Analysis

### Overview

Analyzes the emotional state and urgency level of customer messages to guide response tone and priority.

### When to Use

| Scenario | Use This Skill? |
|----------|-----------------|
| Every incoming customer message | ✅ Always |
| Internal system messages | ❌ No |
| Automated notifications | ❌ No |

### Inputs

```python
{
    "message": {
        "type": "str",
        "description": "The full customer message text to analyze",
        "required": True,
        "examples": [
            "I love NexusFlow! Best tool ever!",
            "This is frustrating, the export keeps failing",
            "HELP!!! Everything disappeared!!!",
            "How do I add a team member?"
        ]
    }
}
```

### Outputs

```python
{
    "message_preview": "str - First 100 chars of message",
    "sentiment": {
        "type": "str",
        "enum": [
            "very_positive",
            "positive",
            "neutral",
            "concerned",
            "frustrated",
            "very_frustrated",
            "panicked",
            "angry"
        ]
    },
    "sentiment_score": "float - Numeric score (-1.0 to 1.0)",
    "urgency": {
        "type": "str",
        "enum": ["none", "low", "medium", "high", "critical"]
    },
    "confidence": "float - Analysis confidence (0.0-1.0)",
    "analyzed_at": "str - ISO timestamp"
}
```

### Sentiment Score Mapping

| Sentiment Label | Score Range | Description |
|-----------------|-------------|-------------|
| `very_positive` | 0.8 - 1.0 | Customer loves the product |
| `positive` | 0.5 - 0.8 | Customer is happy |
| `neutral` | -0.2 - 0.5 | Routine inquiry |
| `concerned` | -0.5 - -0.2 | Customer has worries |
| `frustrated` | -0.7 - -0.5 | Customer is annoyed |
| `very_frustrated` | -0.8 - -0.7 | Customer is quite upset |
| `panicked` | -0.9 - -0.8 | Customer is in crisis |
| `angry` | -1.0 - -0.8 | Customer is mad |

### Implementation Notes

```python
async def sentiment_analysis_skill(message: str) -> dict:
    """
    Analyze the sentiment and urgency of a customer message.
    
    Args:
        message: Customer message text
        
    Returns:
        Dictionary with sentiment label, score, and urgency
    """
    # Call MCP tool
    result = await mcp_client.call_tool("analyze_sentiment", {"message": message})
    data = json.loads(result.content[0].text)
    
    # Map sentiment to score
    sentiment_scores = {
        "very_positive": 1.0,
        "positive": 0.7,
        "neutral": 0.0,
        "concerned": -0.3,
        "frustrated": -0.5,
        "very_frustrated": -0.7,
        "panicked": -0.9,
        "angry": -0.8
    }
    
    return {
        **data,
        "sentiment_score": sentiment_scores.get(data["sentiment"], 0.0)
    }
```

### Urgency Triggers

| Urgency | Trigger Conditions |
|---------|-------------------|
| `critical` | "emergency", "critical", "entire organization", panic indicators (!!!, HELP) |
| `high` | "urgent", "ASAP", "deadline", "tomorrow", presentation/meeting mentioned |
| `medium` | Standard inquiries |
| `low` | "when you get a chance", "no rush", feature requests |
| `none` | Purely positive feedback |

### Related MCP Tool

```python
analyze_sentiment(message: str) → dict
```

---

## Skill 3: Escalation Decision

### Overview

Determines whether a conversation requires human intervention based on multiple factors including sentiment, topic, customer tier, and AI confidence.

### When to Use

| Scenario | Use This Skill? |
|----------|-----------------|
| After generating any response | ✅ Always |
| Before sending response to customer | ✅ Yes |
| When customer requests human | ✅ Yes (immediate escalation) |
| For billing disputes | ✅ Yes (always escalate) |
| For legal/security matters | ✅ Yes (always escalate) |

### Inputs

```python
{
    "conversation_context": {
        "type": "dict",
        "description": "Full conversation state",
        "required": True,
        "fields": {
            "customer_id": "str",
            "message_count": "int",
            "sentiment_history": "list",
            "topics_discussed": "list",
            "channel": "str"
        }
    },
    "sentiment_trend": {
        "type": "str",
        "enum": ["improving", "stable", "declining"],
        "description": "Direction of sentiment change"
    },
    "current_message": {
        "type": "str",
        "description": "The current customer message"
    },
    "response_confidence": {
        "type": "float",
        "description": "AI confidence in generated response (0.0-1.0)"
    },
    "category": {
        "type": "str",
        "description": "Message category (billing, technical, how_to, etc.)"
    }
}
```

### Outputs

```python
{
    "should_escalate": "bool - Whether to escalate to human",
    "reason": "str - Specific reason for escalation (or 'none')",
    "escalation_level": {
        "type": "str",
        "enum": ["L0_AI", "L1_Tier1", "L2_Tier2", "L3_Tier3", "L4_Management"]
    },
    "urgency": {
        "type": "str",
        "enum": ["normal", "high", "critical"]
    },
    "confidence": "float - Confidence in escalation decision (0.0-1.0)"
}
```

### Escalation Rules

| Condition | Escalate? | Level | Reason |
|-----------|-----------|-------|--------|
| Customer requests human | ✅ Yes | L1_Tier1 | Explicit human request |
| Billing dispute (duplicate charge) | ✅ Yes | L1_Tier1 | Requires verification |
| Legal/lawsuit/attorney mentioned | ✅ Yes | L4_Management | Legal matter |
| Security breach mentioned | ✅ Yes | L3_Tier3 | Security incident |
| GDPR/data deletion request | ✅ Yes | L2_Tier2 | Compliance |
| Enterprise contract inquiry | ✅ Yes | L2_Tier2 | Sales handoff |
| Sentiment = panicked | ✅ Yes | L1_Tier1 | VIP treatment |
| Sentiment = very_frustrated + VIP | ✅ Yes | L2_Tier2 | Retention risk |
| Response confidence < 0.5 | ✅ Yes | L1_Tier1 | Low AI confidence |
| Category = data_loss | ✅ Yes | L2_Tier2 | Requires specialist |

### Implementation Notes

```python
async def escalation_decision_skill(
    conversation_context: dict,
    sentiment_trend: str,
    current_message: str,
    response_confidence: float,
    category: str
) -> dict:
    """
    Determine if a conversation requires human escalation.
    
    Args:
        conversation_context: Full conversation state
        sentiment_trend: Direction of sentiment change
        current_message: Current customer message
        response_confidence: AI confidence in response
        category: Message category
        
    Returns:
        Escalation decision with reason and level
    """
    message_lower = current_message.lower()
    
    # Check explicit human request
    if any(phrase in message_lower for phrase in [
        "speak to human", "talk to person", "human agent", "real person"
    ]):
        return {
            "should_escalate": True,
            "reason": "Customer explicitly requested human agent",
            "escalation_level": "L1_Tier1",
            "urgency": "normal",
            "confidence": 1.0
        }
    
    # Check legal/security keywords
    if any(word in message_lower for word in ["lawsuit", "attorney", "lawyer", "court"]):
        return {
            "should_escalate": True,
            "reason": "Legal matter mentioned",
            "escalation_level": "L4_Management",
            "urgency": "critical",
            "confidence": 1.0
        }
    
    # Check billing disputes
    if any(phrase in message_lower for phrase in [
        "charged twice", "duplicate charge", "billing dispute", "wrong charge"
    ]):
        return {
            "should_escalate": True,
            "reason": "Billing dispute requires verification",
            "escalation_level": "L1_Tier1",
            "urgency": "high",
            "confidence": 0.95
        }
    
    # Check low confidence
    if response_confidence < 0.5:
        return {
            "should_escalate": True,
            "reason": f"Low AI confidence ({response_confidence:.2f})",
            "escalation_level": "L1_Tier1",
            "urgency": "normal",
            "confidence": 0.8
        }
    
    # No escalation needed
    return {
        "should_escalate": False,
        "reason": "none",
        "escalation_level": "L0_AI",
        "urgency": "normal",
        "confidence": 0.9
    }
```

### Escalation Level Definitions

| Level | Name | Handles |
|-------|------|---------|
| L0_AI | AI Agent | Routine inquiries, how-to questions |
| L1_Tier1 | General Support | Billing verification, basic requests |
| L2_Tier2 | Technical Specialist | Integrations, advanced features, compliance |
| L3_Tier3 | Senior Engineer | Critical technical issues, VIP customers |
| L4_Management | Executive | Legal, partnerships, major escalations |

### Related MCP Tool

```python
escalate_to_human(ticket_id: str, reason: str, urgency: str) → dict
```

---

## Skill 4: Channel Adaptation

### Overview

Adapts response formatting, tone, and length to match the target communication channel's conventions and constraints.

### When to Use

| Scenario | Use This Skill? |
|----------|-----------------|
| Before sending any customer response | ✅ Always |
| When channel differs from original | ✅ Yes (extra adaptation) |
| For internal notes only | ❌ No |

### Inputs

```python
{
    "response_text": {
        "type": "str",
        "description": "The draft response to format",
        "required": True
    },
    "target_channel": {
        "type": "str",
        "enum": ["email", "whatsapp", "web_form"],
        "description": "Channel to send response on",
        "required": True
    },
    "customer_name": {
        "type": "str",
        "description": "Customer name for personalization",
        "required": False
    },
    "ticket_id": {
        "type": "str",
        "description": "Ticket ID for reference",
        "required": False
    }
}
```

### Outputs

```python
{
    "formatted_response": "str - Channel-appropriate response",
    "channel": "str - Target channel",
    "character_count": "int - Length of formatted response",
    "formatting_applied": {
        "greeting": "str - Type of greeting used",
        "signature": "bool - Whether signature added",
        "emoji": "bool - Whether emoji used",
        "formatting": "str - Any special formatting"
    }
}
```

### Channel Specifications

| Channel | Max Length | Tone | Signature | Emoji | Example |
|---------|------------|------|-----------|-------|---------|
| `email` | Unlimited | Formal | Yes | No | "Dear [Name],\n\n..." |
| `whatsapp` | 300 chars | Casual | No | Yes | "Hey [Name]! 👋..." |
| `web_form` | 1000 chars | Professional | Minimal | Optional | "Hello [Name],\n\n..." |

### Implementation Notes

```python
async def channel_adaptation_skill(
    response_text: str,
    target_channel: str,
    customer_name: str = None,
    ticket_id: str = None
) -> dict:
    """
    Adapt response formatting for the target channel.
    
    Args:
        response_text: Draft response content
        target_channel: Channel to format for
        customer_name: Optional customer name
        ticket_id: Optional ticket reference
        
    Returns:
        Formatted response with metadata
    """
    name = customer_name.split()[0] if customer_name else "there"
    
    if target_channel == "email":
        # Formal email format
        formatted = f"Dear {name},\n\n{response_text}\n\n"
        formatted += "Best regards,\nNexusFlow Support Team\nsupport@nexusflow.com"
        if ticket_id:
            formatted += f"\n\nTicket: {ticket_id}"
        
        return {
            "formatted_response": formatted,
            "channel": "email",
            "character_count": len(formatted),
            "formatting_applied": {
                "greeting": "formal",
                "signature": True,
                "emoji": False,
                "formatting": "paragraphs"
            }
        }
    
    elif target_channel == "whatsapp":
        # Concise, emoji-friendly format
        formatted = f"Hey {name}! 👋\n\n{response_text}"
        # Truncate if too long
        if len(formatted) > 300:
            formatted = formatted[:297] + "..."
        
        return {
            "formatted_response": formatted,
            "channel": "whatsapp",
            "character_count": len(formatted),
            "formatting_applied": {
                "greeting": "casual",
                "signature": False,
                "emoji": True,
                "formatting": "concise"
            }
        }
    
    elif target_channel == "web_form":
        # Professional web form format
        formatted = f"Hello {name},\n\n{response_text}\n\n"
        formatted += "Best regards,\nNexusFlow Support"
        
        return {
            "formatted_response": formatted,
            "channel": "web_form",
            "character_count": len(formatted),
            "formatting_applied": {
                "greeting": "professional",
                "signature": True,
                "emoji": False,
                "formatting": "standard"
            }
        }
```

### Channel Switch Handling

When a customer switches channels mid-conversation:

```python
if conversation.get("channel_switched"):
    # Add continuity note
    previous_channel = conversation["original_channel"]
    formatted = f"(Continuing from {previous_channel}): {formatted}"
```

### Related MCP Tool

```python
send_response(ticket_id: str, message: str, channel: str) → dict
```

---

## Skill 5: Customer Identification

### Overview

Identifies and unifies customer identity across multiple identifiers (email, phone, etc.) to provide consistent service across channels.

### When to Use

| Scenario | Use This Skill? |
|----------|-----------------|
| Every incoming message | ✅ Always (first step) |
| Customer provides new contact info | ✅ Yes (update profile) |
| Channel switch detected | ✅ Yes (verify identity) |
| Internal system messages | ❌ No |

### Inputs

```python
{
    "email": {
        "type": "str",
        "description": "Customer email address",
        "required": False,
        "examples": ["john@company.com", "jane.doe@startup.io"]
    },
    "phone": {
        "type": "str",
        "description": "Customer phone number",
        "required": False,
        "examples": ["+1-555-0123", "+44 20 7946 0958"]
    },
    "name": {
        "type": "str",
        "description": "Customer name (if available)",
        "required": False
    },
    "channel": {
        "type": "str",
        "description": "Channel message arrived on",
        "required": True
    }
}
```

### Outputs

```python
{
    "customer_id": "str - Unified customer identifier",
    "identified": "bool - Whether customer was found in system",
    "customer_profile": {
        "name": "str",
        "email": "str",
        "phone": "str",
        "company": "str",
        "plan": "str",
        "is_vip": "bool"
    },
    "history_summary": {
        "total_conversations": "int",
        "total_messages": "int",
        "topics_discussed": "list",
        "current_sentiment": "str",
        "sentiment_trend": "str",
        "channel_history": "list",
        "last_interaction": "str (ISO timestamp)",
        "status": "str"
    },
    "is_new_customer": "bool - True if first interaction"
}
```

### Identification Priority

| Identifier | Priority | Notes |
|------------|----------|-------|
| Email | 1 (Primary) | Most reliable, used as customer_id |
| Phone | 2 (Secondary) | Used for WhatsApp, fallback |
| Name + Company | 3 (Tertiary) | Weak identifier, use with caution |

### Implementation Notes

```python
async def customer_identification_skill(
    email: str = None,
    phone: str = None,
    name: str = None,
    channel: str = None
) -> dict:
    """
    Identify customer and retrieve their history.
    
    Args:
        email: Customer email address
        phone: Customer phone number
        name: Customer name
        channel: Channel message arrived on
        
    Returns:
        Customer identification with profile and history
    """
    # Determine primary identifier
    customer_id = email if email else phone
    
    if not customer_id:
        # Create temporary ID for anonymous customers
        customer_id = f"anonymous_{uuid.uuid4().hex[:8]}"
        return {
            "customer_id": customer_id,
            "identified": False,
            "customer_profile": {
                "name": name or "Unknown",
                "email": None,
                "phone": None,
                "company": "Unknown",
                "plan": "Unknown",
                "is_vip": False
            },
            "history_summary": None,
            "is_new_customer": True
        }
    
    # Call MCP tool to get history
    result = await mcp_client.call_tool(
        "get_customer_history",
        {"customer_id": customer_id}
    )
    data = json.loads(result.content[0].text)
    
    if data.get("found"):
        return {
            "customer_id": customer_id,
            "identified": True,
            "customer_profile": {
                "name": data.get("name", "Unknown"),
                "email": data.get("email", email),
                "phone": data.get("phone", phone),
                "company": data.get("company", "Unknown"),
                "plan": data.get("plan", "Unknown"),
                "is_vip": data.get("plan") == "Enterprise"
            },
            "history_summary": {
                "total_conversations": 1,
                "total_messages": data.get("total_messages", 0),
                "topics_discussed": data.get("topics_discussed", []),
                "current_sentiment": data.get("current_sentiment", "unknown"),
                "sentiment_trend": data.get("sentiment_trend", "stable"),
                "channel_history": data.get("channel_history", []),
                "last_interaction": data.get("last_interaction", "never"),
                "status": data.get("status", "unknown")
            },
            "is_new_customer": False
        }
    else:
        # Customer not found - new customer
        return {
            "customer_id": customer_id,
            "identified": False,
            "customer_profile": {
                "name": name or customer_id.split("@")[0],
                "email": email,
                "phone": phone,
                "company": "Unknown",
                "plan": "Unknown",
                "is_vip": False
            },
            "history_summary": None,
            "is_new_customer": True
        }
```

### Channel Switch Detection

```python
def detect_channel_switch(current_channel: str, history: dict) -> bool:
    """Detect if customer switched channels."""
    if not history or "channel_history" not in history:
        return False
    
    last_channel = history["channel_history"][-1] if history["channel_history"] else None
    return last_channel != current_channel
```

### Related MCP Tool

```python
get_customer_history(customer_id: str) → dict
```

---

## Example Interaction Flows

### Example 1: Multi-Turn Technical Support (Email)

**Scenario:** Customer Alice reports Gantt export issue, follows up after trying suggestions.

```
═══════════════════════════════════════════════════════════════════════════════
INTERACTION FLOW 1: Technical Support with Follow-up
═══════════════════════════════════════════════════════════════════════════════

MESSAGE 1 (Initial):
────────────────────
From: alice@techcorp.com
Channel: email
Content: "Hi, I'm having trouble exporting my Gantt chart to PDF. It just shows 
         a loading spinner and nothing happens. I have a presentation tomorrow!"

Step 1: Customer Identification
───────────────────────────────
Input:  email="alice@techcorp.com", channel="email"
Output: customer_id="alice@techcorp.com", identified=True
        plan="Professional", is_vip=False
        history_summary: total_messages=0, is_new_customer=True

Step 2: Sentiment Analysis
──────────────────────────
Input:  message="Hi, I'm having trouble exporting my Gantt chart..."
Output: sentiment="panicked", urgency="critical", sentiment_score=-0.9
        (Trigger: "presentation tomorrow" = deadline urgency)

Step 3: Knowledge Retrieval
───────────────────────────
Input:  query="export gantt chart to PDF loading spinner"
Output: articles=[
          {key="gantt_export", title="Exporting Gantt Charts", score=7}
        ]
        confidence=0.7, has_relevant_result=True

Step 4: Generate Response (Internal)
────────────────────────────────────
Draft: "To export a Gantt chart: 1. Open project → 2. Gantt view → 
        3. Export button → 4. Select PDF. If hanging, try reducing 
        visible tasks with filters."

Step 5: Escalation Decision
───────────────────────────
Input:  sentiment="panicked", confidence=0.7, category="technical_issue"
Output: should_escalate=True, reason="Customer is panicked", 
        escalation_level="L1_Tier1", urgency="critical"

Step 6: Channel Adaptation
──────────────────────────
Input:  response=draft, channel="email", name="Alice"
Output: "Dear Alice,\n\nI understand your concern. I'm escalating this 
        to our specialist team. They will reach out within 2 hours.\n\n
        Best regards,\nNexusFlow Support Team\n\nTicket: TKT-20260327-001"

Result: Response sent, ticket escalated to L1_Tier1


MESSAGE 2 (Follow-up, 2 hours later):
─────────────────────────────────────
From: alice@techcorp.com
Channel: email
Content: "Update: I tried reducing visible tasks with filters like you 
         suggested and it worked! The PDF exported successfully. Thank you!"

Step 1: Customer Identification
───────────────────────────────
Input:  email="alice@techcorp.com", channel="email"
Output: customer_id="alice@techcorp.com", identified=True
        history_summary: total_messages=2, topics=["export"], 
        sentiment="panicked", status="escalated"
        → DETECTED: Returning customer with existing conversation

Step 2: Sentiment Analysis
──────────────────────────
Input:  message="Update: I tried reducing visible tasks..."
Output: sentiment="positive", urgency="low", sentiment_score=0.7
        (Trigger: "thank you", "worked")

Step 3: Knowledge Retrieval
───────────────────────────
Input:  query="filter tasks export success"
Output: articles=[], confidence=0.0
        (No KB needed - customer reporting success)

Step 4: Generate Response (Internal)
────────────────────────────────────
Draft: "That's great news! Glad the filter solution worked for you."

Step 5: Escalation Decision
───────────────────────────
Input:  sentiment="positive", confidence=0.9, category="follow-up"
Output: should_escalate=False, reason="none", escalation_level="L0_AI"
        → RESOLVED: Close escalation

Step 6: Channel Adaptation
──────────────────────────
Input:  response=draft, channel="email", name="Alice"
Output: "Dear Alice,\n\nThat's wonderful news! I'm so glad the filter 
        solution worked for your presentation.\n\nBest regards,\n
        NexusFlow Support Team"

Result: Response sent, ticket status changed to "resolved"
```

---

### Example 2: Cross-Channel Support (Web Form → WhatsApp)

**Scenario:** Customer Bob starts on web form, follows up on WhatsApp.

```
═══════════════════════════════════════════════════════════════════════════════
INTERACTION FLOW 2: Cross-Channel Support
═══════════════════════════════════════════════════════════════════════════════

MESSAGE 1 (Web Form):
─────────────────────
From: bob@startup.io
Channel: web_form
Content: "Hello! I'm trying to set up recurring tasks for our weekly team 
         standup meetings. How do I configure the repeat schedule?"

Step 1: Customer Identification
───────────────────────────────
Input:  email="bob@startup.io", channel="web_form"
Output: customer_id="bob@startup.io", identified=False (new customer)
        is_new_customer=True

Step 2: Sentiment Analysis
──────────────────────────
Input:  message="Hello! I'm trying to set up recurring tasks..."
Output: sentiment="neutral", urgency="medium", sentiment_score=0.0

Step 3: Knowledge Retrieval
───────────────────────────
Input:  query="recurring tasks weekly repeat schedule"
Output: articles=[
          {key="recurring_tasks", title="Setting Up Recurring Tasks", score=10}
        ]
        confidence=1.0, has_relevant_result=True

Step 4: Generate Response (Internal)
────────────────────────────────────
Draft: "To create recurring task: 1. Open task → 2. Click 'Repeat' → 
        3. Choose frequency (Daily/Weekly/Monthly) → 4. Select day → 5. Save"

Step 5: Escalation Decision
───────────────────────────
Input:  sentiment="neutral", confidence=1.0, category="how_to"
Output: should_escalate=False, reason="none", escalation_level="L0_AI"

Step 6: Channel Adaptation
──────────────────────────
Input:  response=draft, channel="web_form", name="Bob"
Output: "Hello Bob,\n\nTo create a recurring task:\n1. Open the task (or 
        create new one)\n2. Click the 'Repeat' option\n3. Choose frequency: 
        Daily, Weekly, Bi-weekly, Monthly, Yearly\n4. Select the day(s)\n
        5. Click 'Save'\n\nBest regards,\nNexusFlow Support"

Result: Response sent via web form


MESSAGE 2 (WhatsApp - Channel Switch):
──────────────────────────────────────
From: +1-555-0123 (same customer: bob@startup.io)
Channel: whatsapp
Content: "Thanks! Quick follow-up - can I set different times for each 
         occurrence? Like 9 AM some weeks and 10 AM others?"

Step 1: Customer Identification
───────────────────────────────
Input:  phone="+1-555-0123", channel="whatsapp"
Output: customer_id="bob@startup.io" (linked via phone→email mapping)
        identified=True
        history_summary: total_messages=2, topics=["recurring_tasks"],
        channel_history=["web_form", "whatsapp"]
        → DETECTED: Channel switch from web_form to whatsapp

Step 2: Sentiment Analysis
──────────────────────────
Input:  message="Thanks! Quick follow-up - can I set different times..."
Output: sentiment="positive", urgency="medium", sentiment_score=0.5
        (Trigger: "Thanks!" = positive)

Step 3: Knowledge Retrieval
───────────────────────────
Input:  query="recurring task different times each occurrence"
Output: articles=[], confidence=0.3
        (No KB article covers this specific scenario)

Step 4: Generate Response (Internal)
────────────────────────────────────
Draft: "Currently, recurring tasks use the same time for all occurrences. 
        You can manually adjust individual instances if needed. This is a 
        common feature request."

Step 5: Escalation Decision
───────────────────────────
Input:  sentiment="positive", confidence=0.6, category="feature_inquiry"
Output: should_escalate=False, reason="none", escalation_level="L0_AI"
        Note: Low confidence but not low enough to escalate

Step 6: Channel Adaptation
──────────────────────────
Input:  response=draft, channel="whatsapp", name="Bob"
        channel_switched=True, previous_channel="web_form"
Output: "Hey Bob! 👋\n\n(Continuing from web_form):\n\nCurrently, recurring 
        tasks use the same time for all occurrences. You can manually adjust 
        individual instances if needed. This is actually a common feature 
        request! 📝"
        (Truncated to 300 chars, emoji added)

Result: Response sent via WhatsApp, context preserved from web form
```

---

## MCP Tool Mapping

| Skill | Primary MCP Tool | Secondary MCP Tools |
|-------|------------------|---------------------|
| Knowledge Retrieval | `search_knowledge_base` | - |
| Sentiment Analysis | `analyze_sentiment` | - |
| Escalation Decision | `escalate_to_human` | - |
| Channel Adaptation | `send_response` | - |
| Customer Identification | `get_customer_history` | `create_ticket` (for new customers) |

### Additional Supporting Tools

| Tool | Used By | Purpose |
|------|---------|---------|
| `create_ticket` | Customer Identification | Create ticket for new customers |
| `extract_topics` | Knowledge Retrieval | Enhance search queries |

---

## Skill Composition Patterns

### Standard Response Flow

```python
async def handle_customer_message(message: dict) -> dict:
    # Step 1: Identify customer
    customer = await customer_identification_skill(
        email=message.get("email"),
        phone=message.get("phone"),
        channel=message.get("channel")
    )
    
    # Step 2: Analyze sentiment
    sentiment = await sentiment_analysis_skill(message["content"])
    
    # Step 3: Retrieve knowledge
    knowledge = await knowledge_retrieval_skill(message["content"])
    
    # Step 4: Generate response (internal logic)
    response = generate_response(knowledge, customer, sentiment)
    
    # Step 5: Decide on escalation
    escalation = await escalation_decision_skill(
        conversation_context=customer["history_summary"],
        sentiment_trend=sentiment.get("trend"),
        current_message=message["content"],
        response_confidence=knowledge["confidence"],
        category=detect_category(message["content"])
    )
    
    # Step 6: Adapt for channel
    adapted = await channel_adaptation_skill(
        response_text=response,
        target_channel=message["channel"],
        customer_name=customer["customer_profile"]["name"]
    )
    
    # Send response
    if escalation["should_escalate"]:
        await mcp_client.call_tool("escalate_to_human", {
            "ticket_id": get_ticket_id(),
            "reason": escalation["reason"],
            "urgency": escalation["urgency"]
        })
    
    return await mcp_client.call_tool("send_response", {
        "ticket_id": get_ticket_id(),
        "message": adapted["formatted_response"],
        "channel": message["channel"]
    })
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-03-27 | Initial release with 5 core skills |

---

## Related Documents

- [Exercise 1.4: MCP Server](./mcp-server.md) - Tool implementations
- [Exercise 1.3: Memory & State](./memory-state.md) - Customer history storage
- [Exercise 1.2: Core Loop](./prototype-core-loop.md) - Response generation logic

---

**Document End**
