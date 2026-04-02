# Code Mapping Document

**NexusFlow Customer Success Digital FTE**  
**Transition Phase: Incubation Code → Production Components**

| Document Info | Details |
|---------------|---------|
| Phase | Transition |
| Date | 2026-03-27 |
| Team | Digital FTE Team |
| Status | Ready for Production Development |

---

## Overview

This document maps all Incubation Phase code artifacts to their Production Phase destinations. Each component is analyzed for:
- **Keep As-Is**: Production-ready with minimal changes
- **Refactor**: Needs restructuring for production
- **Replace**: Will be replaced by production technology
- **Extend**: Needs additional features for production

---

## Component Mapping Table

| Incubation Component | Source File | Production Component | Destination | Action | Priority |
|---------------------|-------------|---------------------|-------------|--------|----------|
| **Core Loop Logic** | `src/agent/core_loop.py` | Agent Orchestration | `src/agents/orchestrator.py` | Refactor | P0 |
| **Sentiment Analyzer** | `src/agent/core_loop.py:SentimentAnalyzer` | Sentiment Service | `src/services/sentiment.py` | Keep As-Is | P0 |
| **Knowledge Base** | `src/agent/core_loop.py:KnowledgeBase` | Vector Search Service | `src/services/vector_search.py` | Replace | P1 |
| **Escalation Engine** | `src/agent/core_loop.py:EscalationEngine` | Escalation Service | `src/services/escalation.py` | Keep As-Is | P0 |
| **Response Generator** | `src/agent/core_loop.py:ResponseGenerator` | Response Service | `src/services/response.py` | Extend | P0 |
| **Memory Agent** | `src/agent/memory_agent.py` | Conversation Service | `src/services/conversation.py` | Refactor | P0 |
| **Memory Store (JSON)** | `data/conversations/conversations.json` | PostgreSQL Database | `src/database/models.py` | Replace | P0 |
| **Topic Extractor** | `src/agent/memory_agent.py:TopicExtractor` | Topic Service | `src/services/topic.py` | Keep As-Is | P1 |
| **MCP Server** | `src/mcp_server.py` | OpenAI Function Tools | `src/tools/functions.py` | Refactor | P0 |
| **MCP Tools (7)** | `src/mcp_server.py:list_tools()` | @function_tool decorators | `src/tools/functions.py` | Refactor | P0 |
| **Test Suite (Core)** | `src/agent/test_core_loop.py` | Unit Tests | `tests/unit/test_*.py` | Extend | P1 |
| **Test Suite (Memory)** | `src/agent/test_memory_agent.py` | Integration Tests | `tests/integration/test_*.py` | Extend | P1 |
| **Test Suite (MCP)** | `src/test_mcp_tools.py` | Tool Tests | `tests/unit/test_tools.py` | Extend | P1 |
| **Channel Enums** | `src/agent/core_loop.py:Channel` | Shared Types | `src/types/enums.py` | Keep As-Is | P0 |
| **Data Models** | `src/agent/core_loop.py:Ticket, CustomerProfile` | Pydantic Models | `src/types/models.py` | Refactor | P0 |
| **Context Files** | `context/*.md` | Knowledge Base Content | PostgreSQL `kb_articles` table | Migrate | P1 |
| **Sample Tickets** | `context/sample-tickets.json` | Test Fixtures | `tests/fixtures/tickets.json` | Keep As-Is | P1 |
| **Specifications** | `specs/*.md` | Documentation | `docs/` | Migrate | P2 |

---

## Detailed Mapping

### 1. Agent Components

| Component | Current State | Production State | Changes Required |
|-----------|---------------|------------------|------------------|
| **CustomerSupportAgent** (core_loop.py) | Monolithic agent class | Split into Orchestrator + Services | Extract services, add dependency injection |
| **MemoryAgent** (memory_agent.py) | JSON-based persistence | PostgreSQL-backed service | Replace JSON store with SQLAlchemy models |
| **MCP Server** (mcp_server.py) | stdio MCP protocol | OpenAI @function_tool decorators | Wrap tools as async functions |

### 2. Service Layer

| Service | Source | Destination | Notes |
|---------|--------|-------------|-------|
| **SentimentService** | `core_loop.py:SentimentAnalyzer` | `src/services/sentiment.py` | Add LLM-based sentiment option |
| **KnowledgeService** | `core_loop.py:KnowledgeBase` | `src/services/vector_search.py` | Replace keyword search with embeddings |
| **EscalationService** | `core_loop.py:EscalationEngine` | `src/services/escalation.py` | Add escalation history tracking |
| **ResponseService** | `core_loop.py:ResponseGenerator` | `src/services/response.py` | Add template system |
| **ConversationService** | `memory_agent.py:MemoryStore` | `src/services/conversation.py` | PostgreSQL integration |
| **TopicService** | `memory_agent.py:TopicExtractor` | `src/services/topic.py` | Add LLM-based extraction |

### 3. Data Layer

| Component | Current | Production | Migration Path |
|-----------|---------|------------|----------------|
| **Customer Storage** | JSON dict | PostgreSQL `customers` table | Export JSON → INSERT statements |
| **Conversation Storage** | JSON file | PostgreSQL `conversations` table | Export JSON → INSERT statements |
| **Ticket Storage** | In-memory dict | PostgreSQL `tickets` table | Schema already defined in memory_agent |
| **Escalation Storage** | In-memory dict | PostgreSQL `escalations` table | Add escalation table |
| **Knowledge Base** | Python dict | PostgreSQL `kb_articles` + Vector DB | Export articles → DB migration |

### 4. API Layer

| Component | Current | Production | Notes |
|-----------|---------|------------|-------|
| **MCP Protocol** | stdio transport | OpenAI Functions | Keep logic, change interface |
| **Tool Definitions** | MCP Tool objects | @function_tool decorators | Direct mapping |
| **Tool Handlers** | Async functions | Async functions | Minimal changes |

---

## Production Folder Structure

```
nexusflow-digital-fte/
│
├── README.md
├── requirements.txt
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
│
├── src/
│   ├── __init__.py
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py          # Main agent orchestration
│   │   └── prompts.py               # System prompts
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── functions.py             # OpenAI @function_tool decorators
│   │   └── handlers.py              # Tool execution handlers
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── sentiment.py             # Sentiment analysis
│   │   ├── knowledge.py             # Knowledge base search
│   │   ├── escalation.py            # Escalation logic
│   │   ├── response.py              # Response generation
│   │   ├── conversation.py          # Conversation management
│   │   └── topic.py                 # Topic extraction
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py            # PostgreSQL connection
│   │   ├── models.py                # SQLAlchemy models
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── customer_repo.py
│   │   │   ├── conversation_repo.py
│   │   │   ├── ticket_repo.py
│   │   │   └── escalation_repo.py
│   │   └── migrations/
│   │       ├── versions/
│   │       └── env.py
│   │
│   ├── types/
│   │   ├── __init__.py
│   │   ├── enums.py                 # Channel, Sentiment, Urgency enums
│   │   └── models.py                # Pydantic models
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI application
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── conversations.py
│   │   │   ├── tickets.py
│   │   │   └── escalations.py
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       └── rate_limit.py
│   │
│   ├── channels/
│   │   ├── __init__.py
│   │   ├── email.py                 # Gmail API integration
│   │   ├── whatsapp.py              # WhatsApp Business API
│   │   └── web_form.py              # Web form webhook
│   │
│   ├── queue/
│   │   ├── __init__.py
│   │   ├── kafka_producer.py
│   │   ├── kafka_consumer.py
│   │   └── events.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── logging.py
│       └── helpers.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── fixtures/
│   │   ├── __init__.py
│   │   └── tickets.json
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_sentiment.py
│   │   ├── test_knowledge.py
│   │   ├── test_escalation.py
│   │   ├── test_response.py
│   │   └── test_tools.py
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_conversation.py
│   │   ├── test_database.py
│   │   └── test_channels.py
│   └── e2e/
│       ├── __init__.py
│       └── test_full_flow.py
│
├── docs/
│   ├── architecture.md
│   ├── api-reference.md
│   ├── deployment.md
│   └── runbook.md
│
├── k8s/
│   ├── namespace.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   └── secrets.yaml
│
├── scripts/
│   ├── migrate_data.py
│   ├── seed_kb.py
│   └── deploy.sh
│
└── context/
    ├── brand-voice.md
    ├── company-profile.md
    ├── escalation-rules.md
    ├── product-docs.md
    └── sample-tickets.json
```

---

## Migration Priority

### Phase 1: Core Infrastructure (Week 1-2)

| Component | Files | Priority | Effort |
|-----------|-------|----------|--------|
| Database Models | `src/database/models.py` | P0 | 2 days |
| Service Layer | `src/services/*.py` | P0 | 3 days |
| OpenAI Tools | `src/tools/functions.py` | P0 | 2 days |
| FastAPI Setup | `src/api/main.py` | P0 | 1 day |

### Phase 2: Channel Integrations (Week 2-3)

| Component | Files | Priority | Effort |
|-----------|-------|----------|--------|
| Gmail API | `src/channels/email.py` | P0 | 2 days |
| WhatsApp Business | `src/channels/whatsapp.py` | P0 | 2 days |
| Web Form | `src/channels/web_form.py` | P1 | 1 day |

### Phase 3: Infrastructure (Week 3-4)

| Component | Files | Priority | Effort |
|-----------|-------|----------|--------|
| Kafka Queue | `src/queue/*.py` | P1 | 2 days |
| Docker | `Dockerfile`, `docker-compose.yml` | P1 | 1 day |
| Kubernetes | `k8s/*.yaml` | P1 | 2 days |

### Phase 4: Testing & Documentation (Week 4)

| Component | Files | Priority | Effort |
|-----------|-------|----------|--------|
| Unit Tests | `tests/unit/*.py` | P1 | 2 days |
| Integration Tests | `tests/integration/*.py` | P1 | 2 days |
| Documentation | `docs/*.md` | P2 | 1 day |

---

## Code Reuse Summary

| Category | Reuse Percentage | Notes |
|----------|------------------|-------|
| Business Logic | 85% | Sentiment, escalation, topic extraction reusable |
| Data Models | 60% | Need conversion to Pydantic/SQLAlchemy |
| Tool Handlers | 75% | MCP handlers → OpenAI functions |
| Test Cases | 80% | Existing tests extendable |
| Documentation | 90% | Specs migrate to docs with updates |

---

## Next Steps

1. **Create Production Folder Structure** - Run `mkdir` commands for all directories
2. **Set Up Database** - Create PostgreSQL schema from models
3. **Migrate MCP Tools** - Convert to @function_tool decorators
4. **Implement Service Layer** - Extract logic from monolithic classes
5. **Add Channel Integrations** - Gmail API, WhatsApp Business API
6. **Deploy Infrastructure** - Docker, Kubernetes, Kafka

---

## Final Status

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   ✅ Transition Preparation Complete                                          ║
║                                                                               ║
║   Ready for Step 3: Transform MCP Tools to OpenAI @function_tool              ║
║                                                                               ║
║   All incubation code mapped to production components.                        ║
║   Folder structure defined. Migration priorities set.                         ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
```

---

**Document End**
