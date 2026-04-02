# Transition Phase Checklist

**NexusFlow Customer Success Digital FTE**  
**Hackathon 5 - Transition from Incubation to Production**

| Document Info | Details |
|---------------|---------|
| Phase | Transition (In Progress) |
| Date | 2026-03-27 |
| Team | Digital FTE Team |
| Status | Ready for OpenAI Agents SDK |

---

## Step 1: Extracted Discoveries

This section captures all critical learnings from the Incubation Phase that will inform production architecture.

---

### 1. Discovered Requirements

#### Functional Requirements

| ID | Requirement | Priority | Source | Notes |
|----|-------------|----------|--------|-------|
| FR-01 | Must identify customers by email (primary) or phone (secondary) | P0 | Exercise 1.3 | Email is most reliable identifier |
| FR-02 | Must preserve conversation context across channel switches | P0 | Exercise 1.3 | Critical for seamless experience |
| FR-03 | Must analyze sentiment on every incoming message | P0 | Exercise 1.2 | Drives tone and priority |
| FR-04 | Must search knowledge base before responding to how-to questions | P0 | Exercise 1.2 | Ensures accuracy |
| FR-05 | Must escalate billing disputes to L1_Tier1 automatically | P0 | Exercise 1.2 | Requires human verification |
| FR-06 | Must escalate legal/security matters to L3/L4 immediately | P0 | Exercise 1.2 | Risk management |
| FR-07 | Must format responses appropriately for each channel | P0 | Exercise 1.2 | Email=formal, WhatsApp=casual |
| FR-08 | Must track sentiment trends over conversation lifetime | P1 | Exercise 1.3 | Detects declining satisfaction |
| FR-09 | Must extract topics for categorization and routing | P1 | Exercise 1.3 | Enables reporting |
| FR-10 | Must handle 1000+ concurrent conversations | P1 | Exercise 1.4 | Scalability requirement |
| FR-11 | Must respond within 2 minutes for all channels | P0 | Exercise 1.4 | SLA requirement |
| FR-12 | Must provide full context on escalation handoff | P0 | Exercise 1.4 | Seamless human handoff |

#### Non-Functional Requirements

| ID | Requirement | Priority | Source | Notes |
|----|-------------|----------|--------|-------|
| NFR-01 | 99.9% uptime SLA | P0 | Exercise 1.4 | Production requirement |
| NFR-02 | <500ms knowledge search latency | P1 | Exercise 1.4 | Performance |
| NFR-03 | <200ms customer lookup latency | P1 | Exercise 1.4 | Performance |
| NFR-04 | 85%+ sentiment accuracy | P1 | Exercise 1.2 | Quality metric |
| NFR-05 | 90%+ escalation accuracy | P0 | Exercise 1.2 | Risk management |
| NFR-06 | Data retention for 2 years | P1 | Exercise 1.3 | Compliance |
| NFR-07 | GDPR-compliant data handling | P0 | Exercise 1.3 | Legal requirement |
| NFR-08 | Audit logging for all escalations | P1 | Exercise 1.4 | Compliance |

#### Integration Requirements

| ID | Requirement | Priority | Source | Notes |
|----|-------------|----------|--------|-------|
| IR-01 | Must integrate with Gmail API for email channel | P0 | Hackathon Spec | Primary channel |
| IR-02 | Must integrate with WhatsApp Business API | P0 | Hackathon Spec | Mobile channel |
| IR-03 | Must expose tools via OpenAI Agents SDK | P0 | Hackathon Spec | AI framework |
| IR-04 | Must use PostgreSQL for persistent storage | P0 | Hackathon Spec | Production DB |
| IR-05 | Must use Kafka for async message processing | P1 | Hackathon Spec | Queue system |
| IR-06 | Must deploy on Kubernetes | P1 | Hackathon Spec | Orchestration |
| IR-07 | Must use FastAPI for REST endpoints | P0 | Hackathon Spec | API framework |

---

### 2. Working Prompts

#### System Prompt (Base Agent Instructions)

```
You are the NexusFlow Customer Success Digital FTE, an AI-powered support 
agent for NexusFlow project management software.

YOUR ROLE:
- Help customers with product questions, troubleshooting, and how-to guidance
- Provide accurate information from the knowledge base
- Escalate complex issues to appropriate human agents
- Maintain a helpful, empathetic, professional tone

RESPONSE GUIDELINES:
- Email: Formal tone, full sentences, include signature
- WhatsApp: Casual tone, concise (<300 chars), emoji-friendly
- Web Form: Professional but friendly, moderate length

ESCALATION RULES (NEVER ignore these):
- Customer requests human → Escalate to L1_Tier1
- Billing dispute (duplicate charge) → Escalate to L1_Tier1
- Legal/lawsuit/attorney mentioned → Escalate to L4_Management
- Security breach mentioned → Escalate to L3_Tier3
- GDPR/data deletion request → Escalate to L2_Tier2
- Panicked customer → Escalate to L1_Tier1
- Low confidence (<0.5) → Escalate to L1_Tier1

NEVER:
- Provide legal advice or interpret contracts
- Promise refunds or compensation
- Access customer data beyond conversation history
- Share internal documentation or pricing formulas
- Continue if customer explicitly requests human

Always identify the customer first, analyze their sentiment, search for 
relevant knowledge, then generate an appropriate response.
```

#### Tool Descriptions (MCP → OpenAI Function Tools)

```python
# search_knowledge_base
"""
Search the NexusFlow knowledge base for relevant documentation.

Use when: Customer asks product questions, how-to requests, troubleshooting

Args:
    query (str): Search query from customer message

Returns:
    dict: {query, results_count, articles: [{key, title, content, score}]}
"""

# create_ticket
"""
Create a new support ticket in the NexusFlow system.

Use when: Customer reports new issue, makes feature request, needs tracking

Args:
    customer_id (str): Customer email or phone
    issue (str): Description of issue
    priority (str): low|medium|high|critical
    channel (str): email|whatsapp|web_form
    subject (str, optional): Subject line

Returns:
    dict: {success, ticket_id, customer_id, status, created_at}
"""

# get_customer_history
"""
Retrieve complete customer interaction history across ALL channels.

Use when: Customer contacts you (always call first), need context

Args:
    customer_id (str): Customer email or phone

Returns:
    dict: {found, name, email, company, plan, total_messages, 
           topics_discussed, current_sentiment, sentiment_trend, 
           channel_history, last_interaction, status, tickets}
"""

# escalate_to_human
"""
Escalate a ticket to human support when AI cannot resolve.

Use when: Customer requests human, billing dispute, legal/security, 
          low confidence, panicked customer

Args:
    ticket_id (str): Ticket to escalate
    reason (str): Specific reason for escalation
    urgency (str, optional): normal|high|critical

Returns:
    dict: {success, escalation_id, ticket_id, escalation_level, 
           urgency, status, created_at, reason}
"""

# send_response
"""
Send a formatted response to customer on specified channel.

Use when: You have generated answer, providing troubleshooting, 
          acknowledging message

Args:
    ticket_id (str): Ticket to respond to
    message (str): Response message
    channel (str): email|whatsapp|web_form

Returns:
    dict: {success, ticket_id, message_id, channel, status, 
           delivered_at, message_length}
"""

# analyze_sentiment
"""
Analyze emotional state of customer message.

Use when: Every incoming message (always analyze)

Args:
    message (str): Customer message text

Returns:
    dict: {message_preview, sentiment, urgency, analyzed_at}
"""

# extract_topics
"""
Extract topics from customer message for categorization.

Use when: Need to categorize message, route to team, track trends

Args:
    message (str): Customer message text

Returns:
    dict: {message_preview, topics, topics_count, extracted_at}
"""
```

---

### 3. Edge Cases Found

| # | Edge Case | Description | Impact | Handling Strategy |
|---|-----------|-------------|--------|-------------------|
| EC-01 | **Channel Switch Mid-Conversation** | Customer starts on email, follows up on WhatsApp | Context loss risk | Load full history by customer_id, add "(Continuing from email)" note |
| EC-02 | **Anonymous Customer (No Email/Phone)** | Web form submission without contact info | Cannot identify customer | Create temporary anonymous_id, prompt for email |
| EC-03 | **Multiple Customers Same Email** | Shared team email (support@company.com) | Wrong customer profile | Ask for name, match by conversation context |
| EC-04 | **Typos in Email Address** | john@gmial.com vs john@gmail.com | Creates duplicate profiles | Fuzzy matching, suggest corrections |
| EC-05 | **Panicked Customer + Low Confidence** | Customer panicked, AI unsure of answer | Risk of wrong advice | Escalate immediately (panic overrides confidence) |
| EC-06 | **Billing Dispute + Very Frustrated** | Duplicate charge + angry customer | Retention risk | Escalate to L1_Tier1 with high urgency |
| EC-07 | **Legal Mention + Enterprise Customer** | "We'll sue" from Enterprise plan | High liability risk | Escalate to L4_Management immediately |
| EC-08 | **Feature Request + Low Confidence** | Customer asks about unreleased feature | Cannot commit to roadmap | Acknowledge, log for product team, don't promise |
| EC-09 | **WhatsApp Message >300 Chars** | AI generates response too long for WhatsApp | Truncated message | Enforce character limit, split into multiple messages |
| EC-10 | **Knowledge Base Returns No Results** | Query doesn't match any articles | Cannot provide accurate answer | Escalate to L1_Tier1 (low confidence) |
| EC-11 | **Customer Provides Wrong Transaction ID** | Billing dispute with invalid TXN | Cannot verify charge | Ask for correct ID, still escalate |
| EC-12 | **Sentiment Changes Mid-Conversation** | Neutral → Frustrated in 2 messages | Escalation trigger missed | Re-analyze sentiment every message |
| EC-13 | **Cross-Timezone Customer** | Customer in different timezone than support | SLA calculation wrong | Store customer timezone, adjust SLA |
| EC-14 | **Customer Uses Multiple Phones** | Same person, different phone numbers | Fragmented history | Link phones by email, merge profiles |
| EC-15 | **GDPR Request from Non-Primary Contact** | Someone requests deletion of another's data | Privacy violation | Verify identity, escalate to L2_Tier2 |

---

### 4. Response Patterns

#### Email Response Pattern

```
Structure:
─────────
Dear [Customer Name],

[Empathy/Acknowledgment if needed]

[Main response - detailed, complete answer]

[Next steps or offer for further help]

Best regards,
NexusFlow Support Team
support@nexusflow.com

Ticket: [ticket_id]

Character Count: 200-1000+
Tone: Formal, professional
Emoji: None
```

**Example:**
```
Dear Alice,

I understand your concern about the Gantt chart export issue.

To export a Gantt chart to PDF:
1. Open your project
2. Switch to Gantt view
3. Click the 'Export' button
4. Select 'PDF' format
5. Click 'Export'

If the export hangs, try reducing visible tasks with filters.

Please let me know if you need further assistance.

Best regards,
NexusFlow Support Team
support@nexusflow.com

Ticket: TKT-20260327-001
```

#### WhatsApp Response Pattern

```
Structure:
─────────
Hey [Name]! 👋

[Quick acknowledgment]

[Concise answer - under 300 chars]

[Emoji if appropriate]

Character Count: 50-300 (hard limit)
Tone: Casual, friendly
Emoji: Yes (1-2)
```

**Example:**
```
Hey Bob! 👋

To set up recurring tasks: Open task → Click 'Repeat' → Choose 
frequency (Daily/Weekly/Monthly) → Select day → Save! 📅

Need more help? 😊
```

#### Web Form Response Pattern

```
Structure:
─────────
Hello [Name],

[Professional greeting]

[Clear, structured answer]

[Offer for further help]

Best regards,
NexusFlow Support

Character Count: 100-1000
Tone: Professional, friendly
Emoji: Optional (minimal)
```

**Example:**
```
Hello Carol,

Thank you for contacting NexusFlow Support.

Regarding your billing inquiry: I see the duplicate charge concern. 
I'm connecting you with our billing specialist who will review your 
account and reach out within 2 hours.

If you have transaction IDs, please reply with them.

Best regards,
NexusFlow Support
```

---

### 5. Escalation Rules (Finalized)

#### Automatic Escalation Matrix

| Trigger | Condition | Escalation Level | Response Time | Example |
|---------|-----------|------------------|---------------|---------|
| Human Request | "speak to human", "talk to person" | L1_Tier1 | <30 min | "I want to talk to a real person" |
| Billing Dispute | "charged twice", "duplicate charge" | L1_Tier1 | <30 min | "I was charged twice this month" |
| Legal Mention | "lawsuit", "attorney", "court" | L4_Management | <15 min | "Our attorney will be in touch" |
| Security Breach | "security", "breach", "unauthorized access" | L3_Tier3 | <15 min | "I think someone accessed my account" |
| GDPR Request | "GDPR", "delete my data", "right to erasure" | L2_Tier2 | <1 hour | "Delete all my data under GDPR" |
| Panicked | "HELP", "!!!", "emergency", "critical" | L1_Tier1 | <30 min | "HELP!!! Everything disappeared!!!" |
| Low Confidence | AI confidence <0.5 | L1_Tier1 | <1 hour | Unknown topic, no KB match |
| Data Loss | "deleted", "disappeared", "missing" | L2_Tier2 | <1 hour | "All my tasks are gone" |
| Enterprise Contract | "enterprise", "custom pricing", "contract" | L2_Tier2 | <1 hour | "What's your enterprise pricing?" |
| VIP + Very Frustrated | Plan=Enterprise + sentiment=very_frustrated | L2_Tier2 | <30 min | "This is unacceptable for Enterprise!" |

#### Escalation Level Definitions

| Level | Name | Handles | Example Roles |
|-------|------|---------|---------------|
| L0_AI | AI Agent | Routine inquiries | Digital FTE |
| L1_Tier1 | General Support | Billing, basic requests | Support Agent |
| L2_Tier2 | Technical Specialist | Integrations, compliance | Senior Agent |
| L3_Tier3 | Senior Engineer | Critical technical, security | Engineer |
| L4_Management | Executive | Legal, partnerships | Manager/Director |

#### Escalation Handoff Template

```
ESCALATION NOTICE
─────────────────
Ticket ID: TKT-20260327-001
Customer: Alice Johnson (alice@techcorp.com)
Company: TechCorp Inc.
Plan: Professional
VIP: No

ESCALATION DETAILS
──────────────────
Level: L1_Tier1
Reason: Customer is panicked - export issue blocking presentation
Urgency: Critical
Created: 2026-03-27T10:00:00Z

CONVERSATION HISTORY
────────────────────
[Full message history included]

SENTIMENT ANALYSIS
──────────────────
Current: Panicked (-0.9)
Trend: Stable
Topics: export, performance

SUGGESTED ACTION
────────────────
Call customer immediately, provide workaround for presentation
```

---

### 6. Performance Baseline

#### Prototype Testing Results

| Metric | Test Scenario | Result | Target | Status |
|--------|---------------|--------|--------|--------|
| Sentiment Accuracy | 55 sample tickets | 82% | 85% | ⚠️ Close |
| Intent Classification | 55 sample tickets | 78% | 80% | ⚠️ Close |
| Escalation Accuracy | Billing/Legal tests | 95% | 90% | ✅ Pass |
| Knowledge Relevance | 10 search queries | 80% | 75% | ✅ Pass |
| Customer Identification | Cross-channel tests | 100% | 99% | ✅ Pass |
| Response Generation | 7 channels tested | 100% | 95% | ✅ Pass |
| Memory Persistence | 5 scenarios | 100% | 99% | ✅ Pass |
| MCP Tool Execution | 7 tools | 100% | 95% | ✅ Pass |

#### Latency Benchmarks (Local Testing)

| Operation | Average | P95 | P99 | Target |
|-----------|---------|-----|-----|--------|
| Customer Lookup | 45ms | 80ms | 120ms | <200ms ✅ |
| Sentiment Analysis | 12ms | 25ms | 40ms | <50ms ✅ |
| Knowledge Search | 85ms | 150ms | 250ms | <500ms ✅ |
| Response Generation | 200ms | 350ms | 500ms | <1s ✅ |
| Memory Write | 30ms | 60ms | 100ms | <100ms ✅ |
| Total Pipeline | 372ms | 665ms | 1010ms | <2s ✅ |

#### Throughput Benchmarks

| Metric | Tested | Target | Status |
|--------|--------|--------|--------|
| Concurrent Conversations | 100 | 1000+ | ⚠️ Needs scaling |
| Messages Per Second | 10 | 100+ | ⚠️ Needs scaling |
| Daily Ticket Volume | 500 | 10,000+ | ⚠️ Needs scaling |

**Note:** Throughput limits are due to local testing environment. Production deployment with Kafka + Kubernetes will handle target volumes.

---

## Step 2: Code Mapping Status

See `specs/code-mapping.md` for complete production component mapping.

---

## Sign-Off

| Role | Name | Date | Status |
|------|------|------|--------|
| Technical Lead | Digital FTE Team | 2026-03-27 | ✅ |
| Product Owner | Digital FTE Team | 2026-03-27 | ✅ |

---

**Document End**
