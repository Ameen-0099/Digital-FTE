"""
NexusFlow Customer Success Digital FTE - Memory Agent
======================================================
Exercise 1.3 - Add Memory and State

This module adds persistent conversation memory to the agent system,
allowing context retention across channels and multi-turn conversations.

Features:
- In-memory store with JSON file persistence
- Customer identification by email (primary) or phone
- Full conversation history tracking
- Sentiment trend analysis
- Topic tracking for reporting
- Resolution status management
- Channel switch history

Author: Digital FTE Team
Version: 1.0.0 (Exercise 1.3)
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
from pathlib import Path
import uuid

# Import from core_loop for compatibility
from core_loop import (
    CustomerProfile,
    Channel,
    Sentiment,
    Urgency,
    SentimentAnalyzer,
    KnowledgeBase,
    EscalationEngine,
    EscalationLevel,
    ResponseGenerator
)


# =============================================================================
# DATA MODELS FOR MEMORY
# =============================================================================

class ResolutionStatus(Enum):
    """Ticket resolution status."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_CUSTOMER = "pending_customer"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


@dataclass
class MessageRecord:
    """Single message in conversation history."""
    message_id: str
    timestamp: str
    direction: str  # 'inbound' or 'outbound'
    content: str
    channel: str
    sentiment: str = "neutral"
    topics: List[str] = field(default_factory=list)


@dataclass
class ChannelSwitch:
    """Record of a channel switch event."""
    from_channel: str
    to_channel: str
    timestamp: str
    message_count_before_switch: int


@dataclass
class SentimentSnapshot:
    """Sentiment at a point in time."""
    timestamp: str
    score: float  # -1.0 to 1.0
    label: str


@dataclass
class ConversationMemory:
    """Complete conversation memory for a customer."""
    # Customer identification
    customer_id: str  # Primary key (email or phone)
    customer_name: str
    customer_email: Optional[str]
    customer_phone: Optional[str]
    company: str
    plan: str
    
    # Conversation state
    conversation_id: str
    status: str  # ResolutionStatus
    original_channel: str
    current_channel: str
    channel_switches: List[Dict] = field(default_factory=list)
    
    # Conversation history
    messages: List[Dict] = field(default_factory=list)
    topics_discussed: List[str] = field(default_factory=list)
    
    # Sentiment tracking
    sentiment_history: List[Dict] = field(default_factory=list)
    current_sentiment: str = "neutral"
    sentiment_trend: str = "stable"  # improving, declining, stable
    
    # Metadata
    created_at: str = ""
    updated_at: str = ""
    last_interaction: str = ""
    message_count: int = 0
    resolution_notes: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()
        if not self.last_interaction:
            self.last_interaction = datetime.now().isoformat()


# =============================================================================
# MEMORY STORE - PERSISTENT STORAGE
# =============================================================================

class MemoryStore:
    """
    Persistent memory store for conversations.
    
    Uses in-memory dict for fast access with JSON file persistence.
    In production, this would be replaced with PostgreSQL.
    """
    
    def __init__(self, storage_path: str = "data/conversations"):
        """Initialize memory store with optional custom path."""
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache
        self._conversations: Dict[str, ConversationMemory] = {}
        self._customer_index: Dict[str, str] = {}  # email/phone -> customer_id
        
        # Load existing data
        self._load_from_disk()
    
    def _get_storage_file(self) -> Path:
        """Get the path to the storage JSON file."""
        return self.storage_path / "conversations.json"
    
    def _load_from_disk(self):
        """Load conversations from JSON file."""
        storage_file = self._get_storage_file()
        if not storage_file.exists():
            return
        
        try:
            with open(storage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for conv_data in data.get('conversations', []):
                conv = ConversationMemory(**conv_data)
                self._conversations[conv.customer_id] = conv
                
                # Build index
                if conv.customer_email:
                    self._customer_index[conv.customer_email.lower()] = conv.customer_id
                if conv.customer_phone:
                    self._customer_index[conv.customer_phone] = conv.customer_id
                    
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Could not load conversations: {e}")
    
    def _save_to_disk(self):
        """Persist conversations to JSON file."""
        storage_file = self._get_storage_file()
        
        data = {
            'last_updated': datetime.now().isoformat(),
            'conversation_count': len(self._conversations),
            'conversations': [
                asdict(conv) for conv in self._conversations.values()
            ]
        }
        
        # Write atomically (write to temp, then rename)
        temp_file = storage_file.with_suffix('.tmp')
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        temp_file.replace(storage_file)
    
    def get_or_create_customer_id(self, email: Optional[str], phone: Optional[str]) -> str:
        """
        Get existing customer ID or create new one.
        Email is primary identifier, phone is secondary.
        """
        # Try email first
        if email:
            email_lower = email.lower()
            if email_lower in self._customer_index:
                return self._customer_index[email_lower]
        
        # Try phone
        if phone and phone in self._customer_index:
            return self._customer_index[phone]
        
        # Create new customer ID
        customer_id = email if email else (phone or str(uuid.uuid4()))
        return customer_id
    
    def get_conversation(self, customer_id: str) -> Optional[ConversationMemory]:
        """Get conversation memory for a customer."""
        return self._conversations.get(customer_id)
    
    def create_conversation(self, customer_id: str, customer: CustomerProfile, 
                           channel: str) -> ConversationMemory:
        """Create new conversation memory for a customer."""
        conv = ConversationMemory(
            customer_id=customer_id,
            customer_name=customer.name,
            customer_email=customer.email,
            customer_phone=customer.phone,
            company=customer.company,
            plan=customer.plan,
            conversation_id=f"CONV-{datetime.now().strftime('%Y%m%d')}-{customer_id[:8]}",
            status=ResolutionStatus.OPEN.value,
            original_channel=channel,
            current_channel=channel
        )
        
        self._conversations[customer_id] = conv
        
        # Update index
        if customer.email:
            self._customer_index[customer.email.lower()] = customer_id
        if customer.phone:
            self._customer_index[customer.phone] = customer_id
        
        self._save_to_disk()
        return conv
    
    def update_conversation(self, conv: ConversationMemory):
        """Update conversation memory and persist."""
        conv.updated_at = datetime.now().isoformat()
        conv.last_interaction = datetime.now().isoformat()
        conv.message_count = len(conv.messages)
        
        # Update sentiment trend
        self._update_sentiment_trend(conv)
        
        self._save_to_disk()
    
    def _update_sentiment_trend(self, conv: ConversationMemory):
        """Calculate sentiment trend from history."""
        if len(conv.sentiment_history) < 2:
            conv.sentiment_trend = "stable"
            return
        
        recent = conv.sentiment_history[-3:]
        scores = [s['score'] for s in recent]
        
        if scores[-1] > scores[0] + 0.2:
            conv.sentiment_trend = "improving"
        elif scores[-1] < scores[0] - 0.2:
            conv.sentiment_trend = "declining"
        else:
            conv.sentiment_trend = "stable"
    
    def get_customer_history(self, customer_id: str) -> Optional[Dict]:
        """Get summarized customer history for reporting."""
        conv = self._conversations.get(customer_id)
        if not conv:
            return None
        
        return {
            'customer_id': conv.customer_id,
            'name': conv.customer_name,
            'email': conv.customer_email,
            'company': conv.company,
            'plan': conv.plan,
            'total_conversations': 1,  # Could be extended for multiple conversations
            'total_messages': conv.message_count,
            'topics_discussed': conv.topics_discussed,
            'current_sentiment': conv.current_sentiment,
            'sentiment_trend': conv.sentiment_trend,
            'channel_history': [conv.original_channel, conv.current_channel],
            'last_interaction': conv.last_interaction,
            'status': conv.status
        }
    
    def get_all_conversations(self) -> List[ConversationMemory]:
        """Get all conversations for reporting."""
        return list(self._conversations.values())


# =============================================================================
# TOPIC EXTRACTOR
# =============================================================================

class TopicExtractor:
    """Extract topics from customer messages for tracking."""
    
    TOPIC_KEYWORDS = {
        "pricing": ["price", "cost", "pricing", "plan", "upgrade", "subscription", "tier", "discount"],
        "billing": ["billing", "charge", "payment", "invoice", "refund", "transaction", "duplicate"],
        "export": ["export", "download", "pdf", "csv", "report", "gantt"],
        "integration": ["integration", "slack", "calendar", "github", "salesforce", "api", "sync", "connect"],
        "sso": ["sso", "saml", "login", "authentication", "identity", "okta", "azure"],
        "mobile": ["mobile", "app", "ios", "android", "phone", "tablet", "crash"],
        "recurring_tasks": ["recurring", "repeat", "recurring task", "schedule", "automatic"],
        "guest_access": ["guest", "external", "contractor", "client", "permission", "invite"],
        "time_tracking": ["time", "timer", "tracking", "timesheet", "hours", "billable"],
        "data_loss": ["deleted", "recovery", "restore", "disappeared", "missing", "recover"],
        "performance": ["slow", "performance", "loading", "lag", "speed"],
        "feature_request": ["feature", "request", "wish", "suggest", "add", "would be great"],
        "technical_issue": ["not working", "broken", "error", "issue", "problem", "bug"],
        "onboarding": ["signup", "register", "create account", "getting started", "onboarding", "setup"],
        "compliance": ["gdpr", "soc2", "audit", "compliance", "legal", "security"],
        "training": ["training", "walkthrough", "demo", "learn", "tutorial"]
    }
    
    def extract_topics(self, message: str) -> List[str]:
        """Extract topics from a message."""
        message_lower = message.lower()
        topics = []
        
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            if any(keyword in message_lower for keyword in keywords):
                topics.append(topic)
        
        return topics


# =============================================================================
# MEMORY-AWARE AGENT
# =============================================================================

class MemoryAgent:
    """
    Customer support agent with memory and state management.
    
    Extends the core functionality with:
    - Persistent conversation memory
    - Cross-channel context retention
    - Sentiment trend tracking
    - Topic tracking
    - Memory-aware response generation
    """
    
    def __init__(self, storage_path: str = "data/conversations"):
        """Initialize memory agent with storage."""
        self.memory = MemoryStore(storage_path)
        self.sentiment_analyzer = SentimentAnalyzer()
        self.knowledge_base = KnowledgeBase()
        self.escalation_engine = EscalationEngine()
        self.response_generator = ResponseGenerator()
        self.topic_extractor = TopicExtractor()
    
    def _identify_customer(self, email: Optional[str], phone: Optional[str]) -> str:
        """Identify or create customer ID."""
        return self.memory.get_or_create_customer_id(email, phone)
    
    def _get_or_create_conversation(self, customer_id: str, customer: CustomerProfile, 
                                    channel: str) -> ConversationMemory:
        """Get existing conversation or create new one."""
        conv = self.memory.get_conversation(customer_id)
        
        if conv is None:
            conv = self.memory.create_conversation(customer_id, customer, channel)
        else:
            # Check for channel switch
            if conv.current_channel != channel:
                switch = ChannelSwitch(
                    from_channel=conv.current_channel,
                    to_channel=channel,
                    timestamp=datetime.now().isoformat(),
                    message_count_before_switch=len(conv.messages)
                )
                conv.channel_switches.append(asdict(switch))
                conv.current_channel = channel
        
        return conv
    
    def _calculate_sentiment_score(self, sentiment: Sentiment) -> float:
        """Convert sentiment enum to numeric score."""
        scores = {
            Sentiment.VERY_POSITIVE: 1.0,
            Sentiment.POSITIVE: 0.7,
            Sentiment.NEUTRAL: 0.0,
            Sentiment.CONCERNED: -0.3,
            Sentiment.FRUSTRATED: -0.5,
            Sentiment.VERY_FRUSTRATED: -0.7,
            Sentiment.PANICKED: -0.9,
            Sentiment.ANGRY: -0.8
        }
        return scores.get(sentiment, 0.0)
    
    def _add_message_to_history(self, conv: ConversationMemory, message: str,
                                channel: str, sentiment: Sentiment, 
                                topics: List[str], direction: str = "inbound"):
        """Add message to conversation history."""
        record = MessageRecord(
            message_id=str(uuid.uuid4()),
            timestamp=datetime.now().isoformat(),
            direction=direction,
            content=message,
            channel=channel,
            sentiment=sentiment.value,
            topics=topics
        )
        conv.messages.append(asdict(record))
        
        # Update topics
        for topic in topics:
            if topic not in conv.topics_discussed:
                conv.topics_discussed.append(topic)
        
        # Update sentiment history
        score = self._calculate_sentiment_score(sentiment)
        snapshot = SentimentSnapshot(
            timestamp=datetime.now().isoformat(),
            score=score,
            label=sentiment.value
        )
        conv.sentiment_history.append(asdict(snapshot))
        conv.current_sentiment = sentiment.value
    
    def _generate_memory_aware_response(self, conv: ConversationMemory, 
                                        context: Any, 
                                        kb_results: List[Dict],
                                        category: str,
                                        escalation_needed: bool,
                                        sentiment: Sentiment) -> str:
        """
        Generate response using memory context.
        
        Includes references to previous conversations when relevant.
        """
        # Build memory context string
        memory_context = ""
        
        # Check if this is a follow-up (has previous messages)
        inbound_messages = [m for m in conv.messages if m['direction'] == 'inbound']
        
        if len(inbound_messages) > 1:
            # This is a follow-up - reference previous conversation
            previous_topics = conv.topics_discussed[:-1] if len(conv.topics_discussed) > 1 else []
            
            if previous_topics:
                memory_context = f"As we discussed earlier about {', '.join(previous_topics)}, "
            else:
                memory_context = "Following up on our conversation, "
        
        # Check for channel switch
        if conv.channel_switches:
            last_switch = conv.channel_switches[-1]
            memory_context += f"(Continuing from {last_switch['from_channel']}): "
        
        # Generate base response
        base_response = self.response_generator.generate(
            context, kb_results, category, escalation_needed, sentiment
        )
        
        # Prepend memory context if applicable
        if memory_context:
            # Find a natural insertion point
            lines = base_response.split('\n')
            if len(lines) > 1:
                # Insert after greeting
                lines.insert(1, f"\n{memory_context}")
                base_response = '\n'.join(lines)
            else:
                base_response = f"{memory_context}{base_response}"
        
        return base_response
    
    def process_message(self, message: str, channel: str, customer: CustomerProfile,
                       subject: Optional[str] = None) -> Dict:
        """
        Process incoming message with full memory context.
        
        Args:
            message: Customer message content
            channel: Communication channel (email, whatsapp, web_form)
            customer: Customer profile information
            subject: Optional message subject
            
        Returns:
            Dict with response, metadata, and ticket information
        """
        # Step 1: Identify customer and get/create conversation
        customer_id = self._identify_customer(customer.email, customer.phone)
        conv = self._get_or_create_conversation(customer_id, customer, channel)
        
        # Step 2: Analyze sentiment and urgency
        sentiment, urgency = self.sentiment_analyzer.analyze(message, subject or "")
        
        # Step 3: Extract topics
        topics = self.topic_extractor.extract_topics(message)
        
        # Step 4: Search knowledge base
        kb_results = self.knowledge_base.search(message)
        
        # Step 5: Determine category (simplified intent detection)
        category = self._detect_category(message, subject or "", topics)
        
        # Step 6: Check for escalation
        confidence = 0.8 if kb_results else 0.5
        escalation_needed, escalation_level, escalation_reason = \
            self.escalation_engine.should_escalate(
                message, subject or "", sentiment, urgency, 
                customer, confidence, category
            )
        
        # Step 7: Create message context
        channel_enum = Channel(channel) if isinstance(channel, str) else channel
        msg_context = type('MessageContext', (), {
            'original_message': message,
            'channel': channel_enum,
            'customer': customer,
            'subject': subject,
            'timestamp': datetime.now()
        })()
        
        # Step 8: Generate response with memory context
        response = self._generate_memory_aware_response(
            conv, msg_context, kb_results, category, escalation_needed, sentiment
        )
        
        # Step 9: Add inbound message to history
        self._add_message_to_history(conv, message, channel, sentiment, topics, "inbound")
        
        # Step 10: Add outbound response to history
        self._add_message_to_history(conv, response, channel, sentiment, topics, "outbound")
        
        # Step 11: Update conversation status
        if escalation_needed:
            conv.status = ResolutionStatus.ESCALATED.value
            conv.resolution_notes = escalation_reason
        elif any(word in message.lower() for word in ["thank", "thanks", "resolved", "fixed", "worked", "lifesaver"]):
            conv.status = ResolutionStatus.RESOLVED.value
        else:
            conv.status = ResolutionStatus.IN_PROGRESS.value
        
        # Step 12: Persist updates
        self.memory.update_conversation(conv)
        
        # Step 13: Build result
        ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d')}-{conv.message_count:03d}"
        
        return {
            'response': response,
            'metadata': {
                'customer_id': customer_id,
                'conversation_id': conv.conversation_id,
                'sentiment': sentiment.value,
                'urgency': urgency.value,
                'category': category,
                'confidence': confidence,
                'escalation_needed': escalation_needed,
                'escalation_level': escalation_level.value,
                'escalation_reason': escalation_reason,
                'knowledge_articles_found': len(kb_results),
                'topics': topics,
                'is_follow_up': len(conv.messages) > 2,
                'channel_switched': len(conv.channel_switches) > 0,
                'memory_context_used': len(conv.messages) > 2
            },
            'ticket': {
                'ticket_id': ticket_id,
                'conversation_id': conv.conversation_id,
                'channel': channel,
                'status': conv.status,
                'created_at': conv.created_at
            },
            'memory': {
                'total_messages': conv.message_count,
                'topics_discussed': conv.topics_discussed,
                'sentiment_trend': conv.sentiment_trend,
                'channel_history': [conv.original_channel] + [s['to_channel'] for s in conv.channel_switches]
            }
        }
    
    def _detect_category(self, message: str, subject: str, topics: List[str]) -> str:
        """Detect message category from content and topics."""
        text = (message + " " + subject).lower()
        
        # Check for specific patterns
        if any(word in text for word in ["how do i", "how to", "can you show", "walk me"]):
            return "how_to"
        if any(word in text for word in ["charged twice", "duplicate charge", "billing dispute"]):
            return "billing_dispute"
        if any(word in text for word in ["not working", "broken", "error", "crash"]):
            return "technical_issue"
        if any(word in text for word in ["price", "cost", "upgrade", "plan"]):
            return "pricing_inquiry"
        if any(word in text for word in ["feature request", "would be great", "wish"]):
            return "feature_request"
        if any(word in text for word in ["deleted", "disappeared", "missing"]):
            return "data_loss"
        if any(word in text for word in ["integration", "slack", "api", "sync"]):
            return "integration"
        if any(word in text for word in ["gdpr", "compliance", "audit", "legal"]):
            return "compliance"
        
        # Fall back to first topic
        if topics:
            return topics[0]
        
        return "general"
    
    def get_customer_summary(self, customer_id: str) -> Optional[Dict]:
        """Get summary of customer's conversation history."""
        return self.memory.get_customer_history(customer_id)
    
    def get_all_conversations(self) -> List[Dict]:
        """Get all conversations for reporting."""
        return [
            self.memory.get_customer_history(conv.customer_id)
            for conv in self.memory.get_all_conversations()
        ]


# =============================================================================
# DEMO / TESTING
# =============================================================================

def run_memory_demo():
    """Run demonstration of memory agent capabilities."""
    print("=" * 80)
    print("NEXUSFLOW DIGITAL FTE - MEMORY AGENT DEMO")
    print("Exercise 1.3: Memory and State Management")
    print("=" * 80)
    
    agent = MemoryAgent()
    
    # Scenario 1: Multi-turn conversation on same channel
    print("\n" + "=" * 80)
    print("SCENARIO 1: Multi-turn conversation (Email)")
    print("=" * 80)
    
    customer1 = CustomerProfile(
        name="Alice Johnson",
        email="alice@techcorp.com",
        company="TechCorp",
        plan="Professional"
    )
    
    # First message
    print("\n--- Message 1 (Initial) ---")
    result1 = agent.process_message(
        message="Hi, I'm having trouble exporting my Gantt chart to PDF. It just shows a loading spinner.",
        channel="email",
        customer=customer1,
        subject="Gantt export issue"
    )
    print(f"Sentiment: {result1['metadata']['sentiment']}")
    print(f"Topics: {result1['metadata']['topics']}")
    print(f"Memory used: {result1['metadata']['memory_context_used']}")
    print(f"Response preview: {result1['response'][:200]}...")
    
    # Second message (follow-up)
    print("\n--- Message 2 (Follow-up) ---")
    result2 = agent.process_message(
        message="I tried clearing my cache like you suggested but it's still not working.",
        channel="email",
        customer=customer1,
        subject="Re: Gantt export issue"
    )
    print(f"Is follow-up: {result2['metadata']['is_follow_up']}")
    print(f"Memory used: {result2['metadata']['memory_context_used']}")
    print(f"Topics discussed: {result2['memory']['topics_discussed']}")
    print(f"Response preview: {result2['response'][:200]}...")
    
    # Scenario 2: Cross-channel conversation
    print("\n" + "=" * 80)
    print("SCENARIO 2: Cross-channel (Web Form → WhatsApp)")
    print("=" * 80)
    
    customer2 = CustomerProfile(
        name="Bob Smith",
        email="bob@startup.io",
        company="StartupIO",
        plan="Starter"
    )
    
    # First message on Web Form
    print("\n--- Message 1 (Web Form) ---")
    result3 = agent.process_message(
        message="How do I set up recurring tasks for our weekly standup meetings?",
        channel="web_form",
        customer=customer2,
        subject="Recurring tasks question"
    )
    print(f"Channel: {result3['ticket']['channel']}")
    print(f"Topics: {result3['metadata']['topics']}")
    print(f"Response preview: {result3['response'][:200]}...")
    
    # Follow-up on WhatsApp (channel switch)
    print("\n--- Message 2 (WhatsApp - Channel Switch) ---")
    result4 = agent.process_message(
        message="Thanks! One more thing - can I set different times for each occurrence?",
        channel="whatsapp",
        customer=customer2
    )
    print(f"Channel switched: {result4['metadata']['channel_switched']}")
    print(f"Channel history: {result4['memory']['channel_history']}")
    print(f"Topics discussed: {result4['memory']['topics_discussed']}")
    print(f"Response preview: {result4['response'][:200]}...")
    
    # Scenario 3: Billing dispute with escalation
    print("\n" + "=" * 80)
    print("SCENARIO 3: Billing dispute with sentiment tracking")
    print("=" * 80)
    
    customer3 = CustomerProfile(
        name="Carol White",
        email="carol@enterprise.com",
        company="Enterprise Corp",
        plan="Business",
        is_vip=True
    )
    
    # First message - concerned about billing
    print("\n--- Message 1 (Initial billing concern) ---")
    result5 = agent.process_message(
        message="I think I was charged twice this month. Can you check?",
        channel="email",
        customer=customer3,
        subject="Billing question"
    )
    print(f"Sentiment: {result5['metadata']['sentiment']}")
    print(f"Escalation needed: {result5['metadata']['escalation_needed']}")
    print(f"Reason: {result5['metadata']['escalation_reason']}")
    
    # Second message - more frustrated
    print("\n--- Message 2 (More frustrated) ---")
    result6 = agent.process_message(
        message="This is the second time this has happened! I need this fixed immediately. Transaction IDs: TXN-12345 and TXN-12346",
        channel="email",
        customer=customer3
    )
    print(f"Sentiment: {result6['metadata']['sentiment']}")
    print(f"Sentiment trend: {result6['memory']['sentiment_trend']}")
    print(f"Escalation needed: {result6['metadata']['escalation_needed']}")
    
    # Print customer summary
    print("\n" + "=" * 80)
    print("CUSTOMER SUMMARY (Carol White)")
    print("=" * 80)
    summary = agent.get_customer_summary(customer3.email)
    if summary:
        print(f"Name: {summary['name']}")
        print(f"Company: {summary['company']}")
        print(f"Plan: {summary['plan']}")
        print(f"Total messages: {summary['total_messages']}")
        print(f"Topics discussed: {summary['topics_discussed']}")
        print(f"Current sentiment: {summary['current_sentiment']}")
        print(f"Sentiment trend: {summary['sentiment_trend']}")
        print(f"Status: {summary['status']}")
    
    print("\n" + "=" * 80)
    print("MEMORY AGENT DEMO COMPLETE")
    print("=" * 80)
    print("\nKey Features Demonstrated:")
    print("✓ Multi-turn conversation memory")
    print("✓ Cross-channel context retention")
    print("✓ Sentiment tracking and trend analysis")
    print("✓ Topic tracking across conversation")
    print("✓ Memory-aware response generation")
    print("✓ Escalation with context preservation")
    print("\nData persisted to: data/conversations/conversations.json")


if __name__ == "__main__":
    run_memory_demo()
