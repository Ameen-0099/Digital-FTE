-- =============================================================================
-- NEXUSFLOW CUSTOMER SUCCESS DIGITAL FTE - CRM DATABASE SCHEMA
-- =============================================================================
-- 
-- Purpose: Complete CRM / Ticket Management System for NexusFlow Digital FTE
-- 
-- This schema provides:
--   • Multi-channel customer support (Email, WhatsApp, Web Form)
--   • Cross-conversation memory and context tracking
--   • Vector-based semantic search for knowledge base (pgvector)
--   • Comprehensive reporting and analytics
--   • Full audit trail for compliance
-- 
-- Database: PostgreSQL 14+ with pgvector extension
-- Author: Digital FTE Team
-- Version: 1.0.0 (Production)
-- Created: 2026-03-27
-- 
-- =============================================================================

-- =============================================================================
-- EXTENSIONS
-- =============================================================================

-- Enable pgvector for semantic search (required for knowledge base embeddings)
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enable trigram indexing for fuzzy text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;


-- =============================================================================
-- ENUM TYPES
-- =============================================================================

-- Communication channels supported by the Digital FTE
CREATE TYPE channel_type AS ENUM (
    'email',
    'whatsapp',
    'web_form'
);

-- Customer sentiment categories (from sentiment analysis)
CREATE TYPE sentiment_type AS ENUM (
    'very_positive',
    'positive',
    'neutral',
    'concerned',
    'frustrated',
    'very_frustrated',
    'panicked',
    'angry'
);

-- Ticket urgency levels
CREATE TYPE urgency_type AS ENUM (
    'none',
    'low',
    'medium',
    'high',
    'critical'
);

-- Ticket status in workflow
CREATE TYPE ticket_status_type AS ENUM (
    'open',
    'in_progress',
    'pending_customer',
    'pending_third_party',
    'resolved',
    'closed',
    'escalated'
);

-- Escalation levels for human handoff
CREATE TYPE escalation_level_type AS ENUM (
    'L0_AI',
    'L1_Tier1',
    'L2_Tier2',
    'L3_Tier3',
    'L4_Management'
);

-- Escalation urgency for human agents
CREATE TYPE escalation_urgency_type AS ENUM (
    'normal',
    'high',
    'critical'
);

-- Escalation status
CREATE TYPE escalation_status_type AS ENUM (
    'pending',
    'assigned',
    'in_progress',
    'resolved',
    'closed'
);

-- Message direction (inbound from customer or outbound from agent)
CREATE TYPE message_direction_type AS ENUM (
    'inbound',
    'outbound'
);

-- Customer subscription plans
CREATE TYPE plan_type AS ENUM (
    'free',
    'starter',
    'professional',
    'business',
    'enterprise'
);


-- =============================================================================
-- TABLE: customers
-- =============================================================================
-- Core customer profile table. Stores primary customer information.
-- Each customer can have multiple identifiers (email, phone) for cross-channel matching.
-- =============================================================================

CREATE TABLE customers (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Customer profile information
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    company VARCHAR(255),
    
    -- Subscription details
    plan plan_type DEFAULT 'free',
    is_vip BOOLEAN DEFAULT FALSE,
    
    -- Account metadata
    account_age_days INTEGER DEFAULT 0,
    timezone VARCHAR(50) DEFAULT 'UTC',
    language VARCHAR(10) DEFAULT 'en',
    
    -- Aggregated metrics (updated via triggers)
    total_conversations INTEGER DEFAULT 0,
    total_tickets INTEGER DEFAULT 0,
    total_messages INTEGER DEFAULT 0,
    
    -- Current state
    current_sentiment sentiment_type DEFAULT 'neutral',
    sentiment_trend VARCHAR(20) DEFAULT 'stable',  -- improving, declining, stable
    last_interaction_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_customers_email_format CHECK (email IS NULL OR email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT chk_customers_phone_format CHECK (phone IS NULL OR phone ~* '^\+?[0-9\s\-()]+$'),
    CONSTRAINT chk_customers_sentiment_trend CHECK (sentiment_trend IN ('improving', 'declining', 'stable'))
);

-- Indexes for customers table
CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_phone ON customers(phone);
CREATE INDEX idx_customers_company ON customers(company);
CREATE INDEX idx_customers_plan ON customers(plan);
CREATE INDEX idx_customers_is_vip ON customers(is_vip);
CREATE INDEX idx_customers_created_at ON customers(created_at);
CREATE INDEX idx_customers_last_interaction ON customers(last_interaction_at);

-- Trigram index for fuzzy name/company search
CREATE INDEX idx_customers_name_trgm ON customers USING gin(name gin_trgm_ops);
CREATE INDEX idx_customers_company_trgm ON customers USING gin(company gin_trgm_ops);


-- =============================================================================
-- TABLE: customer_identifiers
-- =============================================================================
-- Cross-channel identity resolution. Links multiple identifiers (email, phone, 
-- external IDs) to a single customer for unified view across channels.
-- =============================================================================

CREATE TABLE customer_identifiers (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Foreign key to customer
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    
    -- Identifier details
    identifier_type VARCHAR(50) NOT NULL,  -- email, phone, whatsapp_id, external_id, etc.
    identifier_value VARCHAR(255) NOT NULL,
    
    -- Verification status
    is_verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMP WITH TIME ZONE,
    
    -- Source of identifier
    source VARCHAR(50) DEFAULT 'manual',  -- manual, gmail, whatsapp, web_form, api
    
    -- Metadata
    is_primary BOOLEAN DEFAULT FALSE,
    notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT uq_customer_identifiers UNIQUE (customer_id, identifier_type, identifier_value)
);

-- Indexes for fast identifier lookup
CREATE INDEX idx_customer_identifiers_value ON customer_identifiers(identifier_value);
CREATE INDEX idx_customer_identifiers_type ON customer_identifiers(identifier_type);
CREATE INDEX idx_customer_identifiers_customer ON customer_identifiers(customer_id);
CREATE INDEX idx_customer_identifiers_primary ON customer_identifiers(is_primary);

-- Composite index for lookup by type and value
CREATE INDEX idx_customer_identifiers_lookup ON customer_identifiers(identifier_type, identifier_value);


-- =============================================================================
-- TABLE: conversations
-- =============================================================================
-- Conversation threads. A conversation can span multiple channels and contains
-- multiple messages. Tracks sentiment evolution and channel switches.
-- =============================================================================

CREATE TABLE conversations (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Foreign key to customer
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    
    -- Conversation metadata
    subject VARCHAR(500),
    original_channel channel_type NOT NULL,
    current_channel channel_type NOT NULL,
    
    -- Channel switch tracking
    channel_switched BOOLEAN DEFAULT FALSE,
    channel_switch_count INTEGER DEFAULT 0,
    
    -- Conversation state
    status VARCHAR(50) DEFAULT 'open',  -- open, in_progress, resolved, closed
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_summary TEXT,
    
    -- Sentiment tracking
    initial_sentiment sentiment_type,
    current_sentiment sentiment_type,
    sentiment_trend VARCHAR(20) DEFAULT 'stable',
    
    -- Topic tracking (stored as JSON array)
    topics_discussed JSONB DEFAULT '[]'::jsonb,
    
    -- Message tracking
    message_count INTEGER DEFAULT 0,
    first_message_at TIMESTAMP WITH TIME ZONE,
    last_message_at TIMESTAMP WITH TIME ZONE,
    
    -- Response time tracking (SLA)
    first_response_at TIMESTAMP WITH TIME ZONE,
    sla_deadline TIMESTAMP WITH TIME ZONE,
    sla_breached BOOLEAN DEFAULT FALSE,
    
    -- Escalation tracking
    is_escalated BOOLEAN DEFAULT FALSE,
    escalation_level escalation_level_type,
    escalation_reason TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_conversations_sentiment_trend CHECK (sentiment_trend IN ('improving', 'declining', 'stable'))
);

-- Indexes for conversations table
CREATE INDEX idx_conversations_customer ON conversations(customer_id);
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_conversations_original_channel ON conversations(original_channel);
CREATE INDEX idx_conversations_current_channel ON conversations(current_channel);
CREATE INDEX idx_conversations_created_at ON conversations(created_at);
CREATE INDEX idx_conversations_last_message ON conversations(last_message_at);
CREATE INDEX idx_conversations_is_escalated ON conversations(is_escalated);
CREATE INDEX idx_conversations_current_sentiment ON conversations(current_sentiment);

-- GIN index for topics JSONB
CREATE INDEX idx_conversations_topics ON conversations USING gin(topics_discussed);

-- Composite indexes for common queries
CREATE INDEX idx_conversations_customer_status ON conversations(customer_id, status);
CREATE INDEX idx_conversations_customer_created ON conversations(customer_id, created_at DESC);


-- =============================================================================
-- TABLE: messages
-- =============================================================================
-- Individual messages within conversations. Tracks full message history with
-- channel, sentiment, and AI generation metadata.
-- =============================================================================

CREATE TABLE messages (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Foreign key to conversation
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    
    -- Message content
    direction message_direction_type NOT NULL,
    content TEXT NOT NULL,
    content_html TEXT,  -- HTML formatted version (for email)
    
    -- Channel tracking (can differ from conversation channel for replies)
    channel channel_type NOT NULL,
    
    -- Message metadata
    subject VARCHAR(500),
    message_id_external VARCHAR(255),  -- External ID (e.g., Gmail Message-ID)
    in_reply_to VARCHAR(255),  -- For threading (email Message-ID references)
    
    -- Sentiment analysis
    sentiment sentiment_type DEFAULT 'neutral',
    sentiment_score DECIMAL(3,2),  -- -1.0 to 1.0
    
    -- AI metadata
    is_ai_generated BOOLEAN DEFAULT FALSE,
    ai_model VARCHAR(50),  -- e.g., "gpt-4", "gpt-4-turbo"
    ai_confidence DECIMAL(3,2),  -- 0.0 to 1.0
    ai_tokens_used INTEGER,
    
    -- Topic extraction
    topics_extracted JSONB DEFAULT '[]'::jsonb,
    
    -- Attachments (stored as JSON array)
    attachments JSONB DEFAULT '[]'::jsonb,
    
    -- Delivery tracking
    delivery_status VARCHAR(50) DEFAULT 'sent',  -- sent, delivered, failed, read
    delivered_at TIMESTAMP WITH TIME ZONE,
    read_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_messages_sentiment_score CHECK (sentiment_score IS NULL OR (sentiment_score >= -1.0 AND sentiment_score <= 1.0)),
    CONSTRAINT chk_messages_ai_confidence CHECK (ai_confidence IS NULL OR (ai_confidence >= 0.0 AND ai_confidence <= 1.0))
);

-- Indexes for messages table
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_messages_direction ON messages(direction);
CREATE INDEX idx_messages_channel ON messages(channel);
CREATE INDEX idx_messages_created_at ON messages(created_at);
CREATE INDEX idx_messages_sentiment ON messages(sentiment);
CREATE INDEX idx_messages_is_ai ON messages(is_ai_generated);

-- GIN index for topics and attachments JSONB
CREATE INDEX idx_messages_topics ON messages USING gin(topics_extracted);
CREATE INDEX idx_messages_attachments ON messages USING gin(attachments);

-- Full-text search index on message content
CREATE INDEX idx_messages_content_fts ON messages USING gin(to_tsvector('english', content));

-- Composite indexes for common queries
CREATE INDEX idx_messages_conversation_created ON messages(conversation_id, created_at);
CREATE INDEX idx_messages_conversation_direction ON messages(conversation_id, direction);


-- =============================================================================
-- TABLE: tickets
-- =============================================================================
-- Support tickets. Denormalized view for quick reporting. Each ticket links to
-- a conversation and tracks status, priority, and resolution.
-- =============================================================================

CREATE TABLE tickets (
    -- Primary key (human-readable format: TKT-YYYYMMDD-XXXXXX)
    id VARCHAR(50) PRIMARY KEY,
    
    -- Foreign keys
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    
    -- Ticket details
    subject VARCHAR(500) NOT NULL,
    description TEXT,
    
    -- Channel and priority
    channel channel_type NOT NULL,
    priority urgency_type DEFAULT 'medium',
    
    -- Ticket state
    status ticket_status_type DEFAULT 'open',
    
    -- Assignment
    assigned_to UUID,  -- References users table (if implemented)
    assigned_at TIMESTAMP WITH TIME ZONE,
    
    -- Response tracking
    first_response_at TIMESTAMP WITH TIME ZONE,
    last_response_at TIMESTAMP WITH TIME ZONE,
    response_count INTEGER DEFAULT 0,
    
    -- Resolution
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by VARCHAR(50),  -- AI or human agent ID
    resolution_summary TEXT,
    resolution_category VARCHAR(100),  -- how_to, technical_issue, billing, etc.
    
    -- SLA tracking
    sla_target_hours INTEGER,
    sla_deadline TIMESTAMP WITH TIME ZONE,
    sla_breached BOOLEAN DEFAULT FALSE,
    
    -- Satisfaction (CSAT)
    csat_score INTEGER CHECK (csat_score IS NULL OR (csat_score >= 1 AND csat_score <= 5)),
    csat_feedback TEXT,
    
    -- Escalation tracking
    escalation_level escalation_level_type,
    escalation_reason TEXT,
    escalated_at TIMESTAMP WITH TIME ZONE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_tickets_id_format CHECK (id ~* '^TKT-[0-9]{8}-[A-Z0-9]{6}$')
);

-- Indexes for tickets table
CREATE INDEX idx_tickets_conversation ON tickets(conversation_id);
CREATE INDEX idx_tickets_customer ON tickets(customer_id);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_priority ON tickets(priority);
CREATE INDEX idx_tickets_channel ON tickets(channel);
CREATE INDEX idx_tickets_created_at ON tickets(created_at);
CREATE INDEX idx_tickets_resolved_at ON tickets(resolved_at);
CREATE INDEX idx_tickets_assigned_to ON tickets(assigned_to);
CREATE INDEX idx_tickets_escalation_level ON tickets(escalation_level);

-- Composite indexes for common queries
CREATE INDEX idx_tickets_customer_status ON tickets(customer_id, status);
CREATE INDEX idx_tickets_status_created ON tickets(status, created_at);
CREATE INDEX idx_tickets_customer_created ON tickets(customer_id, created_at DESC);
CREATE INDEX idx_tickets_priority_status ON tickets(priority, status);


-- =============================================================================
-- TABLE: escalations
-- =============================================================================
-- Escalation records for human handoff. Tracks full escalation lifecycle.
-- =============================================================================

CREATE TABLE escalations (
    -- Primary key (human-readable format: ESC-YYYYMMDD-XXXXX)
    id VARCHAR(50) PRIMARY KEY,
    
    -- Foreign keys
    ticket_id VARCHAR(50) NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    
    -- Escalation details
    reason TEXT NOT NULL,
    escalation_level escalation_level_type NOT NULL,
    urgency escalation_urgency_type DEFAULT 'normal',
    status escalation_status_type DEFAULT 'pending',
    
    -- Assignment
    assigned_to UUID,  -- Human agent ID
    assigned_at TIMESTAMP WITH TIME ZONE,
    accepted_at TIMESTAMP WITH TIME ZONE,
    
    -- Resolution
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolution_notes TEXT,
    
    -- Handoff context (JSON for flexibility)
    handoff_context JSONB DEFAULT '{}'::jsonb,  -- Includes conversation summary, sentiment, topics
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_escalations_id_format CHECK (id ~* '^ESC-[0-9]{8}-[A-Z0-9]{5}$')
);

-- Indexes for escalations table
CREATE INDEX idx_escalations_ticket ON escalations(ticket_id);
CREATE INDEX idx_escalations_conversation ON escalations(conversation_id);
CREATE INDEX idx_escalations_customer ON escalations(customer_id);
CREATE INDEX idx_escalations_status ON escalations(status);
CREATE INDEX idx_escalations_level ON escalations(escalation_level);
CREATE INDEX idx_escalations_urgency ON escalations(urgency);
CREATE INDEX idx_escalations_assigned_to ON escalations(assigned_to);
CREATE INDEX idx_escalations_created_at ON escalations(created_at);

-- GIN index for handoff context JSONB
CREATE INDEX idx_escalations_handoff_context ON escalations USING gin(handoff_context);


-- =============================================================================
-- TABLE: knowledge_base
-- =============================================================================
-- Knowledge base articles with pgvector embeddings for semantic search.
-- Enables AI to find relevant articles using vector similarity.
-- =============================================================================

CREATE TABLE knowledge_base (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Article metadata
    key VARCHAR(100) UNIQUE NOT NULL,  -- Short identifier (e.g., "gantt_export")
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    content_html TEXT,  -- HTML formatted version
    
    -- Categorization
    category VARCHAR(100),
    tags TEXT[],  -- Array of tags
    
    -- Search keywords (for keyword-based fallback)
    keywords TEXT[],
    
    -- Vector embedding for semantic search (OpenAI text-embedding-3-small = 1536 dims)
    embedding vector(1536),
    
    -- Article status
    status VARCHAR(50) DEFAULT 'published',  -- draft, published, archived
    is_featured BOOLEAN DEFAULT FALSE,
    
    -- Usage tracking
    view_count INTEGER DEFAULT 0,
    helpful_count INTEGER DEFAULT 0,
    not_helpful_count INTEGER DEFAULT 0,
    
    -- Versioning
    version INTEGER DEFAULT 1,
    previous_version_id UUID REFERENCES knowledge_base(id),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT chk_kb_status CHECK (status IN ('draft', 'published', 'archived'))
);

-- Indexes for knowledge_base table
CREATE INDEX idx_kb_key ON knowledge_base(key);
CREATE INDEX idx_kb_category ON knowledge_base(category);
CREATE INDEX idx_kb_status ON knowledge_base(status);
CREATE INDEX idx_kb_is_featured ON knowledge_base(is_featured);
CREATE INDEX idx_kb_created_at ON knowledge_base(created_at);

-- GIN index for tags and keywords arrays
CREATE INDEX idx_kb_tags ON knowledge_base USING gin(tags);
CREATE INDEX idx_kb_keywords ON knowledge_base USING gin(keywords);

-- Full-text search index on title and content
CREATE INDEX idx_kb_content_fts ON knowledge_base USING gin(to_tsvector('english', title || ' ' || content));

-- TRIGRAM index for fuzzy title search
CREATE INDEX idx_kb_title_trgm ON knowledge_base USING gin(title gin_trgm_ops);

-- =============================================================================
-- VECTOR INDEX FOR SEMANTIC SEARCH (pgvector ivfflat)
-- =============================================================================
-- This index enables fast approximate nearest neighbor search for embeddings.
-- Lists parameter: sqrt(number_of_rows) is a good starting point.
-- =============================================================================

CREATE INDEX idx_kb_embedding ON knowledge_base USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);


-- =============================================================================
-- TABLE: channel_configs
-- =============================================================================
-- Configuration for each communication channel. Stores API credentials,
-- rate limits, and channel-specific settings.
-- =============================================================================

CREATE TABLE channel_configs (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Channel identification
    channel channel_type UNIQUE NOT NULL,
    
    -- Configuration (stored as JSON for flexibility)
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    
    -- API credentials (encrypted at application layer)
    api_key_encrypted BYTEA,
    api_secret_encrypted BYTEA,
    
    -- Rate limiting
    rate_limit_per_minute INTEGER DEFAULT 60,
    rate_limit_per_day INTEGER DEFAULT 10000,
    
    -- Channel-specific settings
    is_enabled BOOLEAN DEFAULT TRUE,
    is_primary BOOLEAN DEFAULT FALSE,
    
    -- Health monitoring
    last_health_check_at TIMESTAMP WITH TIME ZONE,
    health_status VARCHAR(50) DEFAULT 'unknown',  -- healthy, degraded, down
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_channel_config CHECK (
        (channel = 'email' AND config ? 'smtp_host') OR
        (channel = 'whatsapp' AND config ? 'phone_number_id') OR
        (channel = 'web_form' AND config ? 'webhook_url')
    )
);

-- Indexes for channel_configs table
CREATE INDEX idx_channel_configs_channel ON channel_configs(channel);
CREATE INDEX idx_channel_configs_enabled ON channel_configs(is_enabled);
CREATE INDEX idx_channel_configs_health ON channel_configs(health_status);


-- =============================================================================
-- TABLE: agent_metrics
-- =============================================================================
-- Aggregated metrics for the Digital FTE agent. Updated periodically for
-- reporting and monitoring dashboards.
-- =============================================================================

CREATE TABLE agent_metrics (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Time period
    metric_date DATE NOT NULL,
    metric_hour INTEGER,  -- For hourly breakdown (0-23), NULL for daily aggregates
    
    -- Volume metrics
    total_conversations INTEGER DEFAULT 0,
    total_messages INTEGER DEFAULT 0,
    total_tickets INTEGER DEFAULT 0,
    total_escalations INTEGER DEFAULT 0,
    
    -- Channel breakdown (stored as JSON)
    conversations_by_channel JSONB DEFAULT '{}'::jsonb,
    messages_by_channel JSONB DEFAULT '{}'::jsonb,
    
    -- Sentiment distribution (stored as JSON)
    sentiment_distribution JSONB DEFAULT '{}'::jsonb,
    
    -- Resolution metrics
    ai_resolved_count INTEGER DEFAULT 0,
    human_resolved_count INTEGER DEFAULT 0,
    ai_resolution_rate DECIMAL(5,2) DEFAULT 0,  -- Percentage
    
    -- Response time metrics (in seconds)
    avg_first_response_time DECIMAL(10,2),
    p50_first_response_time DECIMAL(10,2),
    p95_first_response_time DECIMAL(10,2),
    p99_first_response_time DECIMAL(10,2),
    
    -- Resolution time metrics (in seconds)
    avg_resolution_time DECIMAL(10,2),
    p50_resolution_time DECIMAL(10,2),
    p95_resolution_time DECIMAL(10,2),
    p99_resolution_time DECIMAL(10,2),
    
    -- SLA metrics
    sla_breach_count INTEGER DEFAULT 0,
    sla_compliance_rate DECIMAL(5,2) DEFAULT 100,  -- Percentage
    
    -- Escalation metrics
    escalations_by_level JSONB DEFAULT '{}'::jsonb,
    escalation_rate DECIMAL(5,2) DEFAULT 0,  -- Percentage
    
    -- Quality metrics
    avg_csat_score DECIMAL(3,2),
    csat_response_count INTEGER DEFAULT 0,
    
    -- AI performance
    avg_ai_confidence DECIMAL(5,2),
    low_confidence_count INTEGER DEFAULT 0,  -- Confidence < 0.5
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT chk_metrics_date_hour CHECK (
        (metric_hour IS NULL) OR (metric_hour >= 0 AND metric_hour <= 23)
    ),
    CONSTRAINT chk_metrics_percentage CHECK (
        ai_resolution_rate >= 0 AND ai_resolution_rate <= 100 AND
        sla_compliance_rate >= 0 AND sla_compliance_rate <= 100 AND
        escalation_rate >= 0 AND escalation_rate <= 100
    )
);

-- Indexes for agent_metrics table
CREATE INDEX idx_metrics_date ON agent_metrics(metric_date);
CREATE INDEX idx_metrics_hour ON agent_metrics(metric_hour);
CREATE INDEX idx_metrics_date_hour ON agent_metrics(metric_date, metric_hour);

-- Unique constraint for date/hour combination
CREATE UNIQUE INDEX idx_metrics_unique_period ON agent_metrics(metric_date, metric_hour);


-- =============================================================================
-- TRIGGERS
-- =============================================================================

-- Trigger function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to all tables with updated_at column
CREATE TRIGGER update_customers_updated_at
    BEFORE UPDATE ON customers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_customer_identifiers_updated_at
    BEFORE UPDATE ON customer_identifiers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tickets_updated_at
    BEFORE UPDATE ON tickets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_escalations_updated_at
    BEFORE UPDATE ON escalations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_knowledge_base_updated_at
    BEFORE UPDATE ON knowledge_base
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_channel_configs_updated_at
    BEFORE UPDATE ON channel_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agent_metrics_updated_at
    BEFORE UPDATE ON agent_metrics
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- =============================================================================
-- VIEWS
-- =============================================================================

-- View: Customer 360 (unified customer view with all identifiers)
CREATE VIEW customer_360 AS
SELECT 
    c.id,
    c.name,
    c.email,
    c.phone,
    c.company,
    c.plan,
    c.is_vip,
    c.current_sentiment,
    c.sentiment_trend,
    c.total_conversations,
    c.total_tickets,
    c.total_messages,
    c.last_interaction_at,
    c.created_at,
    json_agg(
        json_build_object(
            'type', ci.identifier_type,
            'value', ci.identifier_value,
            'verified', ci.is_verified,
            'primary', ci.is_primary
        )
    ) FILTER (WHERE ci.id IS NOT NULL) as identifiers
FROM customers c
LEFT JOIN customer_identifiers ci ON c.id = ci.customer_id
GROUP BY c.id;

-- View: Active Conversations (conversations not yet resolved)
CREATE VIEW active_conversations AS
SELECT 
    conv.id,
    conv.customer_id,
    cust.name as customer_name,
    cust.email as customer_email,
    cust.plan as customer_plan,
    conv.subject,
    conv.original_channel,
    conv.current_channel,
    conv.channel_switched,
    conv.current_sentiment,
    conv.message_count,
    conv.first_message_at,
    conv.last_message_at,
    conv.is_escalated,
    conv.escalation_level,
    conv.created_at,
    t.id as ticket_id,
    t.priority as ticket_priority,
    t.status as ticket_status
FROM conversations conv
JOIN customers cust ON conv.customer_id = cust.id
LEFT JOIN tickets t ON conv.id = t.conversation_id
WHERE conv.is_resolved = FALSE;

-- View: Today's Metrics (real-time metrics for current day)
CREATE VIEW todays_metrics AS
SELECT 
    metric_date,
    total_conversations,
    total_messages,
    total_tickets,
    total_escalations,
    ai_resolved_count,
    human_resolved_count,
    ai_resolution_rate,
    avg_first_response_time,
    avg_resolution_time,
    sla_compliance_rate,
    escalation_rate,
    avg_csat_score
FROM agent_metrics
WHERE metric_date = CURRENT_DATE;


-- =============================================================================
-- INITIAL DATA
-- =============================================================================

-- Insert default channel configurations
INSERT INTO channel_configs (channel, config, is_primary) VALUES
    ('email', '{"smtp_host": "smtp.nexusflow.com", "smtp_port": 587, "from_address": "support@nexusflow.com"}'::jsonb, TRUE),
    ('whatsapp', '{"phone_number_id": "", "business_account_id": ""}'::jsonb, FALSE),
    ('web_form', '{"webhook_url": "https://app.nexusflow.com/api/support/webhook"}'::jsonb, FALSE)
ON CONFLICT (channel) DO NOTHING;


-- =============================================================================
-- SCHEMA DOCUMENTATION
-- =============================================================================

-- Add comments to tables for documentation
COMMENT ON TABLE customers IS 'Core customer profiles with aggregated metrics';
COMMENT ON TABLE customer_identifiers IS 'Cross-channel identity resolution for unified customer view';
COMMENT ON TABLE conversations IS 'Conversation threads with sentiment and channel tracking';
COMMENT ON TABLE messages IS 'Individual messages with AI metadata and sentiment analysis';
COMMENT ON TABLE tickets IS 'Support tickets for workflow and SLA tracking';
COMMENT ON TABLE escalations IS 'Human handoff records with full context';
COMMENT ON TABLE knowledge_base IS 'Product documentation with vector embeddings for semantic search';
COMMENT ON TABLE channel_configs IS 'Channel API configurations and rate limits';
COMMENT ON TABLE agent_metrics IS 'Aggregated daily/hourly metrics for reporting dashboards';


-- =============================================================================
-- END OF SCHEMA
-- =============================================================================
