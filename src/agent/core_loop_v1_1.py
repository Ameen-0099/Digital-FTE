"""
NexusFlow Customer Success Digital FTE - Core Loop Prototype
=============================================================
Exercise 1.2 - Prototype the Core Loop

Iteration 1: Added proper handling for pricing-related queries using escalation rules.
Billing disputes and duplicate charges now escalate appropriately.

Author: Digital FTE Team
Version: 1.1.0 (Iteration 1 - Pricing Handling)
"""

import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


# =============================================================================
# DATA MODELS
# =============================================================================

class Channel(Enum):
    """Supported communication channels."""
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    WEB_FORM = "web_form"


class Sentiment(Enum):
    """Customer sentiment categories."""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    CONCERNED = "concerned"
    FRUSTRATED = "frustrated"
    VERY_FRUSTRATED = "very_frustrated"
    PANICKED = "panicked"
    ANGRY = "angry"


class Urgency(Enum):
    """Ticket urgency levels."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EscalationLevel(Enum):
    """Support escalation levels."""
    L0_AI = "L0_AI"  # Fully automated
    L1_TIER1 = "L1_Tier1"  # General support agent
    L2_TIER2 = "L2_Tier2"  # Technical specialist
    L3_TIER3 = "L3_Tier3"  # Senior engineer
    L4_MANAGEMENT = "L4_Management"  # Executive/management


@dataclass
class CustomerProfile:
    """Customer information for context-aware responses."""
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: str = "Unknown"
    plan: str = "Free"
    account_age_days: int = 0
    is_vip: bool = False


@dataclass
class Ticket:
    """Support ticket record."""
    ticket_id: str
    channel: str
    customer_name: str
    customer_email: Optional[str]
    subject: str
    message: str
    sentiment: str
    urgency: str
    category: str
    escalation_level: str
    escalation_reason: Optional[str]
    response: str
    created_at: str
    status: str = "open"


@dataclass
class MessageContext:
    """Normalized message context for processing."""
    original_message: str
    channel: Channel
    customer: CustomerProfile
    subject: Optional[str]
    timestamp: datetime


# =============================================================================
# KNOWLEDGE BASE (Extracted from product-docs.md)
# =============================================================================

class KnowledgeBase:
    """
    Simple knowledge base extracted from product documentation.
    In production, this would be a vector database or search index.
    """
    
    def __init__(self):
        self.articles = {
            "getting_started": {
                "title": "Getting Started with NexusFlow",
                "content": "To create your account: Visit app.nexusflow.com, click 'Start Free Trial', enter your work email, verify, and complete onboarding. System Requirements: Web: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+. Mobile: iOS 15+, Android 10+.",
                "keywords": ["signup", "register", "create account", "getting started", "onboarding", "setup"]
            },
            "pricing": {
                "title": "NexusFlow Pricing Plans",
                "content": "Free Plan ($0/user/month): Up to 3 projects, 100MB storage. Starter Plan ($12/user/month): Unlimited projects, 10GB storage, Gantt charts. Professional Plan ($24/user/month): Everything in Starter, 100GB storage, Resource management, Time tracking, Integrations. Business Plan ($45/user/month): Everything in Professional, Unlimited storage, Advanced analytics, Custom fields, Priority support. Enterprise Plan (Custom pricing): Everything in Business, SSO/SAML, Dedicated CSM, Custom contracts. Discounts: Annual billing 20% off, Nonprofit 50% off.",
                "keywords": ["pricing", "cost", "price", "plan", "upgrade", "subscription", "tier"]
            },
            "billing_help": {
                "title": "Billing Support & Payment Issues",
                "content": "For billing issues: If you see duplicate charges, contact support immediately. Provide transaction IDs for faster resolution. Refunds are processed within 3-5 business days. Download invoices from Settings → Billing → Invoices. Add VAT number in Billing Settings for EU customers. Upgrade anytime - changes apply immediately. Downgrade applies at next billing cycle. Contact billing team: billing@nexusflow.com",
                "keywords": ["billing", "charge", "payment", "invoice", "refund", "duplicate", "transaction"]
            },
            "recurring_tasks": {
                "title": "Setting Up Recurring Tasks",
                "content": "To create a recurring task: 1. Open the task (or create a new one). 2. Click the 'Repeat' option in the task details. 3. Choose frequency: Daily, Weekly, Bi-weekly, Monthly, Yearly. 4. Select the day(s) of week or date of month. 5. Click 'Save'. The task will automatically generate new instances based on your schedule.",
                "keywords": ["recurring", "repeat", "recurring task", "schedule", "automatic", "periodic"]
            },
            "gantt_export": {
                "title": "Exporting Gantt Charts",
                "content": "To export a Gantt chart to PDF: 1. Open your project. 2. Switch to Gantt view. 3. Click the 'Export' button. 4. Select 'PDF' format. 5. Click 'Export'. The export will generate within 30-60 seconds. Troubleshooting: If export hangs, try reducing visible tasks with filters. Clear browser cache. Use Chrome for best compatibility.",
                "keywords": ["export", "gantt", "pdf", "download", "print", "report"]
            },
            "integrations": {
                "title": "NexusFlow Integrations",
                "content": "Popular Integrations: Slack (notifications in channels), Google Calendar (sync due dates), GitHub/GitLab (link commits), Salesforce (sync customer data), Zapier/Make (5000+ apps). API Access: REST API available for all plans. Rate limits vary by plan (Free: 60/min, Enterprise: custom).",
                "keywords": ["integration", "slack", "calendar", "github", "salesforce", "zapier", "api", "connect"]
            },
            "guest_access": {
                "title": "Adding Guest Members",
                "content": "To add a guest member: 1. Go to Settings → Team → Members. 2. Click '+ Invite Member'. 3. Enter their email. 4. Select role: 'Guest'. 5. Choose which projects they can access. Guest permissions: Can view assigned projects only, can comment and complete tasks, cannot create projects or access billing.",
                "keywords": ["guest", "external", "contractor", "client", "permission", "access", "invite"]
            },
            "time_tracking": {
                "title": "Time Tracking Guide",
                "content": "Starting a timer: 1. Open any task. 2. Click the play timer icon. 3. Work on your task. 4. Click stop when done. Manual time entry: Open task → Time tab → '+ Add Time' → Enter date, duration, description. Time tracking is available on Professional plan and above.",
                "keywords": ["time", "timer", "tracking", "timesheet", "hours", "billable"]
            },
            "sso_setup": {
                "title": "SSO/SAML Configuration",
                "content": "SSO Setup for Enterprise: 1. Contact NexusFlow support to enable SSO. 2. Provide your IdP metadata XML. 3. Configure SAML settings. 4. Test with a pilot user. Supported IdPs: Okta, Azure AD, OneLogin, Generic SAML 2.0. If SSO fails: Verify certificate, check ACS URL, ensure user emails match.",
                "keywords": ["sso", "saml", "login", "authentication", "identity", "okta", "azure ad", "enterprise"]
            },
            "mobile_app": {
                "title": "Mobile App Guide",
                "content": "Mobile App Features: View and edit tasks, receive push notifications, comment and attach photos, start/stop time timer. Troubleshooting crashes: 1. Update to latest app version. 2. Clear app cache. 3. Reinstall the app. 4. Check device storage (need 100MB free). Contact support with device model and OS version.",
                "keywords": ["mobile", "app", "ios", "android", "phone", "tablet", "crash"]
            },
            "data_recovery": {
                "title": "Data Recovery & Deleted Items",
                "content": "Recovering Deleted Data: Go to Settings → Data → Recently Deleted. Items are retained for 30 days. Click 'Restore' to recover. For urgent data recovery: Contact support immediately, provide approximate deletion time, include project/task names if known.",
                "keywords": ["deleted", "recovery", "restore", "disappeared", "missing", "recover"]
            }
        }
        
        # Category mappings for intent detection - Iteration 1: Added billing_dispute
        self.intent_patterns = {
            "how_to": ["how do i", "how to", "can you show", "walk me through", "steps to"],
            "technical_issue": ["not working", "broken", "error", "issue", "problem", "crash", "failed"],
            "billing_dispute": ["charged twice", "duplicate charge", "double charge", "billing dispute", "wrong charge", "transaction"],
            "billing_inquiry": ["billing", "payment", "invoice", "refund", "cost"],
            "feature_request": ["feature request", "would be great", "wish you had", "suggest", "add"],
            "integration": ["integration", "connect", "sync", "slack", "salesforce", "api", "webhook"],
            "account": ["account", "login", "password", "sso", "access", "invite", "user"],
            "pricing_inquiry": ["price", "cost", "upgrade", "plan", "pricing", "discount", "subscription"],
            "export": ["export", "download", "pdf", "csv", "report"],
            "compliance": ["gdpr", "soc2", "audit", "compliance", "legal", "security"],
            "data_loss": ["disappeared", "deleted", "missing", "can't find", "gone", "lost"]
        }

    def search(self, query: str) -> List[Dict]:
        """Search knowledge base for relevant articles."""
        query_lower = query.lower()
        results = []
        
        for key, article in self.articles.items():
            score = 0
            if key.replace("_", " ") in query_lower:
                score += 3
            for keyword in article["keywords"]:
                if keyword in query_lower:
                    score += 2
            if any(word in article["content"].lower() for word in query_lower.split()):
                score += 1
            
            if score > 0:
                results.append({
                    "key": key,
                    "title": article["title"],
                    "content": article["content"],
                    "score": score
                })
        
        # Boost exact phrase matches for critical categories
        # Data loss queries should prioritize data_recovery
        if ("deleted" in query_lower or "disappeared" in query_lower or "missing" in query_lower or "lost" in query_lower) and \
           ("task" in query_lower or "data" in query_lower or "project" in query_lower):
            for article in results:
                if article["key"] == "data_recovery":
                    article["score"] *= 3
        
        # Billing queries should prioritize billing_help
        if ("charge" in query_lower or "billing" in query_lower or "payment" in query_lower or "refund" in query_lower or "transaction" in query_lower):
            for article in results:
                if article["key"] == "billing_help":
                    article["score"] *= 2
        
        # SSO/Login queries should prioritize sso_setup
        if ("sso" in query_lower or "login" in query_lower or "authentication" in query_lower or "saml" in query_lower):
            for article in results:
                if article["key"] == "sso_setup":
                    article["score"] *= 3
        
        # Export queries should prioritize gantt_export
        if ("export" in query_lower and ("gantt" in query_lower or "pdf" in query_lower)):
            for article in results:
                if article["key"] == "gantt_export":
                    article["score"] *= 2
        
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:3]

    def get_article(self, key: str) -> Optional[Dict]:
        """Get a specific article by key."""
        return self.articles.get(key)


# =============================================================================
# SENTIMENT ANALYSIS - Iteration 1: Added billing urgency
# =============================================================================

class SentimentAnalyzer:
    """Rule-based sentiment analyzer for customer messages."""
    
    POSITIVE_WORDS = ["love", "great", "amazing", "awesome", "excellent", "fantastic", "wonderful", "helpful", "thanks", "thank", "appreciate", "obsessed", "happy", "pleased", "satisfied", "perfect", "best"]
    NEGATIVE_WORDS = ["frustrated", "frustrating", "angry", "annoyed", "annoying", "disappointed", "disappointing", "terrible", "horrible", "awful", "useless", "waste", "hate", "worst", "broken", "issue", "problem"]
    URGENCY_WORDS = ["urgent", "asap", "immediately", "critical", "emergency", "deadline", "tomorrow", "right now", "blocking", "down"]
    PANIC_INDICATORS = ["!!!", "???", "HELP", "URGENT", "CRITICAL", "EMERGENCY", "everything disappeared", "all my", "entire", "can't access anything"]
    BILLING_URGENCY_WORDS = ["charged twice", "duplicate", "wrong charge", "unauthorized", "transaction", "refund", "dispute"]
    
    def analyze(self, message: str, subject: str = "") -> Tuple[Sentiment, Urgency]:
        """Analyze message sentiment and urgency."""
        text = (message + " " + subject).lower()
        
        positive_count = sum(1 for word in self.POSITIVE_WORDS if word in text)
        negative_count = sum(1 for word in self.NEGATIVE_WORDS if word in text)
        urgency_count = sum(1 for word in self.URGENCY_WORDS if word in text)
        panic_count = sum(1 for indicator in self.PANIC_INDICATORS if indicator.lower() in text.lower())
        
        has_positive_emoji = any(e in message for e in ["🙌", "🎉", "😊", "👍", "❤️"])
        has_negative_emoji = any(e in message for e in ["😤", "😰", "😱", "🤬", "😡"])
        has_billing_issue = any(word in text for word in self.BILLING_URGENCY_WORDS)
        
        # Determine sentiment
        if panic_count >= 1 or "can't access" in text or "everything disappeared" in text:
            sentiment = Sentiment.PANICKED
        elif negative_count >= 3 or (negative_count >= 2 and "escalat" in text):
            sentiment = Sentiment.VERY_FRUSTRATED
        elif negative_count >= 1 or has_negative_emoji:
            sentiment = Sentiment.FRUSTRATED
        elif "concern" in text or "worry" in text or has_billing_issue:
            sentiment = Sentiment.CONCERNED
        elif positive_count >= 2 or has_positive_emoji:
            sentiment = Sentiment.VERY_POSITIVE if positive_count >= 3 or "love" in text else Sentiment.POSITIVE
        else:
            sentiment = Sentiment.NEUTRAL
        
        # Determine urgency - Iteration 1: Billing issues are higher urgency
        if panic_count >= 1 or "critical" in text or "entire organization" in text:
            urgency = Urgency.CRITICAL
        elif urgency_count >= 2 or "presentation tomorrow" in text or "deadline" in text:
            urgency = Urgency.HIGH
        elif urgency_count >= 1 or "urgent" in text:
            urgency = Urgency.HIGH
        elif has_billing_issue:
            urgency = Urgency.HIGH  # Iteration 1: Billing issues are high urgency
        elif "asap" in text or "soon" in text:
            urgency = Urgency.MEDIUM
        elif "when you get a chance" in text or "no rush" in text:
            urgency = Urgency.LOW
        else:
            urgency = Urgency.MEDIUM
        
        return sentiment, urgency


# =============================================================================
# ESCALATION ENGINE - Iteration 1: Enhanced pricing/billing rules
# =============================================================================

class EscalationEngine:
    """Determines if a ticket should be escalated to human support."""
    
    ALWAYS_ESCALATE_TOPICS = ["legal", "lawsuit", "attorney", "lawyer", "court", "discovery", "security breach", "data breach", "unauthorized access", "partnership", "acquisition", "investment", "enterprise contract", "custom development", "dedicated instance", "on-premise"]
    USUALLY_ESCALATE_TOPICS = ["refund", "chargeback", "duplicate charge", "billing dispute", "cancellation", "churn", "competitor", "switching to", "gdpr deletion", "right to erasure", "soc2", "audit"]
    PRICING_ESCALATION_TOPICS = ["charged twice", "duplicate charge", "double charge", "wrong charge", "billing error", "overcharge", "transaction id", "refund request", "enterprise pricing", "custom pricing", "volume discount", "contract negotiation", "annual contract"]
    
    def should_escalate(self, message: str, subject: str, sentiment: Sentiment, urgency: Urgency, customer: CustomerProfile, confidence: float, category: str) -> Tuple[bool, EscalationLevel, str]:
        """Determine if escalation is needed."""
        text = (message + " " + subject).lower()
        
        # Explicit human request
        if "speak to human" in text or "talk to person" in text or "human agent" in text:
            return True, EscalationLevel.L1_TIER1, "Customer explicitly requested human agent"
        if "manager" in text or "supervisor" in text:
            return True, EscalationLevel.L2_TIER2, "Customer requested manager/supervisor"
        
        # Always-escalate topics
        for topic in self.ALWAYS_ESCALATE_TOPICS:
            if topic in text:
                if topic in ["legal", "lawsuit", "attorney"]:
                    return True, EscalationLevel.L4_MANAGEMENT, f"Legal matter: {topic}"
                elif topic in ["security breach", "data breach"]:
                    return True, EscalationLevel.L3_TIER3, f"Security incident: {topic}"
                return True, EscalationLevel.L2_TIER2, f"Topic requires human: {topic}"
        
        # Iteration 1: Pricing/billing escalation
        for topic in self.PRICING_ESCALATION_TOPICS:
            if topic in text:
                if "charged twice" in text or "duplicate charge" in text or "transaction" in text:
                    return True, EscalationLevel.L1_TIER1, f"Billing dispute requires verification: {topic}"
                elif "enterprise pricing" in text or "custom pricing" in text:
                    return True, EscalationLevel.L2_TIER2, f"Pricing requires sales: {topic}"
                return True, EscalationLevel.L1_TIER1, f"Pricing/billing requires human: {topic}"
        
        # Usually-escalate topics
        for topic in self.USUALLY_ESCALATE_TOPICS:
            if topic in text:
                return True, EscalationLevel.L1_TIER1, f"Topic requires human: {topic}"
        
        # Sentiment-based
        if sentiment == Sentiment.PANICKED:
            return True, EscalationLevel.L1_TIER1, "Customer is panicked"
        if sentiment == Sentiment.VERY_FRUSTRATED and customer.is_vip:
            return True, EscalationLevel.L2_TIER2, "VIP customer very frustrated"
        
        # Urgency-based
        if urgency == Urgency.CRITICAL:
            return True, EscalationLevel.L3_TIER3 if customer.is_vip else EscalationLevel.L2_TIER2, "Critical urgency"
        
        # Confidence-based
        if confidence < 0.6:
            return True, EscalationLevel.L1_TIER1, f"Low AI confidence ({confidence:.2f})"
        
        # Plan-based
        if customer.plan == "Enterprise" and sentiment in [Sentiment.FRUSTRATED, Sentiment.CONCERNED]:
            return True, EscalationLevel.L1_TIER1, "Enterprise with negative sentiment"
        
        # Category-based - Iteration 1
        if category == "billing_dispute":
            return True, EscalationLevel.L1_TIER1, "Billing disputes require human"
        if category == "data_loss":
            return True, EscalationLevel.L2_TIER2, "Data loss requires specialist"
        
        return False, EscalationLevel.L0_AI, "Can be handled by AI"


# =============================================================================
# RESPONSE GENERATOR - Iteration 1: Pricing-specific responses
# =============================================================================

class ResponseGenerator:
    """Generates customer responses based on channel, sentiment, and content."""
    
    EMAIL_GREETINGS = {
        Sentiment.VERY_POSITIVE: "Dear {name},\n\nThank you so much for your kind words!",
        Sentiment.POSITIVE: "Hi {name},\n\nThanks for reaching out!",
        Sentiment.NEUTRAL: "Hello {name},\n\nThank you for contacting NexusFlow Support.",
        Sentiment.CONCERNED: "Hi {name},\n\nI understand your concern, and I'm here to help.",
        Sentiment.FRUSTRATED: "Dear {name},\n\nI sincerely apologize for the frustration.",
        Sentiment.VERY_FRUSTRATED: "Dear {name},\n\nI want to personally apologize.",
        Sentiment.PANICKED: "Hi {name},\n\nDon't worry - I'm here to help!"
    }
    
    EMAIL_SIGNATURE = "\n\nBest regards,\nNexusFlow Support Team\nsupport@nexusflow.com\n\nTicket: {ticket_id}"
    
    WHATSAPP_OPENERS = {
        Sentiment.VERY_POSITIVE: "Hey {name}! Thanks for the love! 🙌",
        Sentiment.POSITIVE: "Hey {name}! 👋",
        Sentiment.NEUTRAL: "Hi {name}!",
        Sentiment.CONCERNED: "Hi {name}, I understand.",
        Sentiment.FRUSTRATED: "Hi {name}, sorry about this! 😕",
        Sentiment.PANICKED: "Hi {name}, don't worry! On it now! 🚨"
    }
    
    WEB_FORM_GREETINGS = {
        Sentiment.VERY_POSITIVE: "Hello {name},\n\nThank you for the feedback!",
        Sentiment.POSITIVE: "Hello {name},\n\nThanks for contacting us!",
        Sentiment.NEUTRAL: "Hello {name},\n\nThank you for your inquiry.",
        Sentiment.CONCERNED: "Hello {name},\n\nI understand your concern.",
        Sentiment.FRUSTRATED: "Hello {name},\n\nI apologize for the inconvenience."
    }
    
    PRICING_RESPONSES = {
        "general": "Plans: Free $0 (3 projects), Starter $12 (unlimited), Pro $24 (time tracking), Business $45 (analytics). Annual = 20% off! Nonprofits = 50% off!",
        "billing_dispute": "I see the billing concern. Connecting you with billing specialist who can review transactions and process refunds. They'll reach out within 2 hours! 🔧"
    }
    
    # Greeting and casual conversation responses
    GREETING_RESPONSES = [
        "Hello! 👋 How can I help you today?",
        "Hi there! What can I assist you with?",
        "Hey! Feel free to ask me anything about NexusFlow.",
    ]
    
    CASUAL_RESPONSES = {
        "hello": "Hello! 👋 How can I assist you today? Feel free to ask about features, pricing, or any issues you're having.",
        "hi": "Hi there! 👋 What can I help you with?",
        "hey": "Hey! How's it going? Need help with anything?",
        "good morning": "Good morning! ☀️ How can I help you today?",
        "good afternoon": "Good afternoon! What can I assist you with?",
        "how are you": "I'm doing great, thank you! 😊 How can I help you with NexusFlow today?",
        "how's it going": "Going well, thanks! What can I help you with?",
        "thanks": "You're welcome! Is there anything else I can help you with?",
        "thank you": "You're welcome! Feel free to ask if you need anything else. 😊",
    }
    
    def generate(self, context: MessageContext, knowledge_results: List[Dict], category: str, escalation_needed: bool, sentiment: Sentiment) -> str:
        """Generate response based on channel and context."""
        # Check for greetings and casual conversation first
        message_lower = context.original_message.lower().strip()
        
        # Handle simple greetings without escalation
        for greeting in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]:
            if message_lower == greeting or message_lower.startswith(greeting + " "):
                return self._generate_casual_response(context, message_lower, sentiment)
        
        # Handle "how are you" and similar
        if any(phrase in message_lower for phrase in ["how are you", "how's it going", "how do you do"]):
            return self._generate_casual_response(context, message_lower, sentiment)
        
        # Handle thanks
        if any(phrase in message_lower for phrase in ["thanks", "thank you", "appreciate"]):
            return self._generate_casual_response(context, message_lower, sentiment)
        
        if context.channel == Channel.WHATSAPP:
            return self._generate_whatsapp(context, knowledge_results, category, sentiment, escalation_needed)
        elif context.channel == Channel.EMAIL:
            return self._generate_email(context, knowledge_results, category, escalation_needed, sentiment)
        return self._generate_webform(context, knowledge_results, category, escalation_needed, sentiment)
    
    def _generate_casual_response(self, context: MessageContext, message_lower: str, sentiment: Sentiment) -> str:
        """Generate casual conversation response."""
        name = context.customer.name.split()[0]
        
        # Find matching casual response
        response = None
        for key, value in self.CASUAL_RESPONSES.items():
            if key in message_lower:
                response = value
                break
        
        if not response:
            response = f"Hello {name}! 👋 How can I help you today?"
        
        return response
    
    def _generate_email(self, context: MessageContext, kb_results: List[Dict], category: str, escalate: bool, sentiment: Sentiment) -> str:
        name = context.customer.name.split()[0]
        greeting = self.EMAIL_GREETINGS.get(sentiment, self.EMAIL_GREETINGS[Sentiment.NEUTRAL]).format(name=name)

        body_parts = []
        if escalate:
            if category in ["billing_dispute", "billing_inquiry"]:
                body_parts.append("\n\nI understand your billing concern. I'm escalating to our billing specialist who will review your account and reach out within 2 hours.\n\nIf you have transaction IDs, please reply with them.\n")
            else:
                body_parts.append("\n\nI'm escalating this to our specialist team. They will reach out within 2 hours.\n")
            # Still include KB content for escalated tickets
            if kb_results:
                body_parts.append(f"\n\nIn the meantime, here's some information that may help:\n\n")
                body_parts.append(kb_results[0]["content"])
        elif category == "pricing_inquiry":
            body_parts.append("\n\nThank you for your pricing inquiry!\n\n")
            body_parts.append(self.PRICING_RESPONSES["general"])
            body_parts.append("\n\nFor personalized recommendations, I can connect you with sales. Would you like that?")
        elif kb_results:
            body_parts.append(f"\n\nRegarding {category.replace('_', ' ')}:\n\n")
            body_parts.append(kb_results[0]["content"])
        else:
            body_parts.append("\n\nI'm looking into this and will update you shortly.\n")

        body_parts.append("\n\nPlease let me know if you need further assistance.")
        ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d')}-001"
        return f"{greeting}{''.join(body_parts)}{self.EMAIL_SIGNATURE.format(ticket_id=ticket_id)}"

    def _generate_whatsapp(self, context: MessageContext, kb_results: List[Dict], category: str, sentiment: Sentiment, escalate: bool) -> str:
        name = context.customer.name.split()[0]
        opener = self.WHATSAPP_OPENERS.get(sentiment, self.WHATSAPP_OPENERS[Sentiment.NEUTRAL]).format(name=name)

        # Iteration 1: Special handling for billing disputes
        if category == "billing_dispute" and escalate:
            response = f"{opener}\n\n{self.PRICING_RESPONSES['billing_dispute']}"
            return response[:300] if len(response) > 300 else response

        # Iteration 1: Pricing inquiries
        if category == "pricing_inquiry":
            response = f"{opener}\n\n{self.PRICING_RESPONSES['general']}\n\nWhich fits your team? 🤔"
            return response[:300] if len(response) > 300 else response

        # For escalated tickets, still include KB content
        if escalate and kb_results:
            content = kb_results[0]["content"][:200] + "..." if len(kb_results[0]["content"]) > 200 else kb_results[0]["content"]
            response = f"{opener}\n\nI'm escalating this to our specialist team. In the meantime:\n\n{content}\n\nNeed more help? 😊"
        elif kb_results:
            content = kb_results[0]["content"][:200] + "..." if len(kb_results[0]["content"]) > 200 else kb_results[0]["content"]
            response = f"{opener}\n\n{content}\n\nNeed more help? 😊"
        else:
            response = f"{opener}\n\nLooking into this! 🔍"

        return response[:300] if len(response) > 300 else response

    def _generate_webform(self, context: MessageContext, kb_results: List[Dict], category: str, escalate: bool, sentiment: Sentiment) -> str:
        name = context.customer.name.split()[0]
        greeting = self.WEB_FORM_GREETINGS.get(sentiment, self.WEB_FORM_GREETINGS[Sentiment.NEUTRAL]).format(name=name)

        body_parts = []
        if escalate:
            if category in ["billing_dispute", "billing_inquiry"]:
                body_parts.append("\n\nI understand your billing concern. Escalating to billing specialist. Update within 2 hours.\n")
            else:
                body_parts.append("\n\nEscalating to specialist team. Update within 4 hours.\n")
            # Still include KB content for escalated tickets
            if kb_results:
                article = kb_results[0]
                body_parts.append(f"\n\nIn the meantime, here's information that may help:\n\n")
                body_parts.append(f"{article['title']}\n\n")
                body_parts.append(article["content"])
        elif category == "pricing_inquiry":
            body_parts.append("\n\n")
            body_parts.append(self.PRICING_RESPONSES["general"])
        elif kb_results:
            # Use KB content with proper formatting
            article = kb_results[0]
            body_parts.append(f"\n\n{article['title']}\n\n")
            body_parts.append(article["content"])
            if len(kb_results) > 1:
                body_parts.append(f"\n\nSee also: {kb_results[1]['title']}")
        else:
            body_parts.append("\n\nInvestigating and will update soon.\n")

        body_parts.append("\n\nBest regards,\nNexusFlow Support Team")
        return f"{greeting}{''.join(body_parts)}"


# =============================================================================
# INTENT CLASSIFIER
# =============================================================================

class IntentClassifier:
    """Classifies customer intent from message content."""

    # Map knowledge base article keys to intent categories
    KB_TO_INTENT_MAP = {
        "getting_started": "how_to",
        "pricing": "pricing_inquiry",
        "billing_help": "billing_inquiry",
        "recurring_tasks": "how_to",
        "gantt_export": "export",
        "integrations": "integration",
        "guest_access": "how_to",
        "time_tracking": "how_to",
        "sso_setup": "technical_issue",
        "mobile_app": "technical_issue",
        "data_recovery": "data_loss",
    }
    
    # Casual conversation patterns that should NOT be escalated
    CASUAL_PATTERNS = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening", 
                       "how are you", "how's it going", "thanks", "thank you", "appreciate"]

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self.patterns = kb.intent_patterns

    def classify(self, message: str, subject: str = "") -> Tuple[str, float]:
        """Classify message intent."""
        text = (message + " " + subject).lower()
        scores = {}
        
        # Check for casual conversation - return early with high confidence
        for pattern in self.CASUAL_PATTERNS:
            if pattern in text:
                return "casual", 0.95  # High confidence for casual chat

        # Step 1: Pattern-based intent detection
        for intent, patterns in self.patterns.items():
            score = sum(1 for p in patterns if p in text)
            if score > 0:
                scores[intent] = score

        # Step 2: Knowledge base search - map KB articles to intents
        kb_results = self.kb.search(text)
        if kb_results and kb_results[0]["score"] > 2:
            top_article_key = kb_results[0]["key"]
            # Map KB article to its corresponding intent
            mapped_intent = self.KB_TO_INTENT_MAP.get(top_article_key)
            if mapped_intent:
                # Boost the score for the mapped intent
                kb_score = kb_results[0]["score"]
                if mapped_intent in scores:
                    scores[mapped_intent] += kb_score  # Add to existing score
                else:
                    scores[mapped_intent] = kb_score  # Create new score

        if not scores:
            return "general_inquiry", 0.5

        best = max(scores, key=scores.get)
        return best, min(scores[best] / 5.0, 1.0)


# =============================================================================
# TICKET MANAGER
# =============================================================================

class TicketManager:
    """Creates and manages support tickets."""
    
    def __init__(self):
        self.counter = 0
    
    def create_ticket(self, context: MessageContext, sentiment: Sentiment, urgency: Urgency, category: str, escalation_level: EscalationLevel, escalation_reason: Optional[str], response: str) -> Ticket:
        self.counter += 1
        ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d')}-{self.counter:03d}"
        subject = context.subject if context.subject else context.original_message[:50] + "..."
        
        return Ticket(
            ticket_id=ticket_id,
            channel=context.channel.value,
            customer_name=context.customer.name,
            customer_email=context.customer.email,
            subject=subject,
            message=context.original_message[:500],
            sentiment=sentiment.value,
            urgency=urgency.value,
            category=category,
            escalation_level=escalation_level.value,
            escalation_reason=escalation_reason,
            response=response,
            created_at=datetime.now().isoformat(),
            status="escalated" if escalation_level != EscalationLevel.L0_AI else "resolved"
        )


# =============================================================================
# CORE LOOP - MAIN AGENT
# =============================================================================

class CustomerSupportAgent:
    """Main Customer Success Digital FTE agent."""
    
    def __init__(self):
        self.kb = KnowledgeBase()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.escalation_engine = EscalationEngine()
        self.response_generator = ResponseGenerator()
        self.intent_classifier = IntentClassifier(self.kb)
        self.ticket_manager = TicketManager()
    
    def process_message(self, message: str, channel: str, customer: Optional[CustomerProfile] = None, subject: Optional[str] = None) -> Dict:
        """Process an incoming customer message."""
        # Normalize channel
        try:
            channel_enum = Channel(channel.lower())
        except ValueError:
            channel_enum = Channel.WEB_FORM
        
        # Default customer
        if customer is None:
            customer = CustomerProfile(name="Valued Customer", email="customer@example.com", company="Unknown", plan="Free")
        
        # Create context
        context = MessageContext(original_message=message, channel=channel_enum, customer=customer, subject=subject, timestamp=datetime.now())
        
        # Analyze
        sentiment, urgency = self.sentiment_analyzer.analyze(message, subject or "")
        category, confidence = self.intent_classifier.classify(message, subject or "")
        kb_results = self.kb.search(message)
        
        # Escalate
        escalate, esc_level, esc_reason = self.escalation_engine.should_escalate(
            message=message, subject=subject or "", sentiment=sentiment, urgency=urgency,
            customer=customer, confidence=confidence, category=category
        )
        
        # Generate response
        response = self.response_generator.generate(context, kb_results, category, escalate, sentiment)
        
        # Create ticket
        ticket = self.ticket_manager.create_ticket(context, sentiment, urgency, category, esc_level, esc_reason, response)
        
        return {
            "success": True,
            "response": response,
            "ticket": asdict(ticket),
            "metadata": {
                "channel": channel_enum.value,
                "sentiment": sentiment.value,
                "urgency": urgency.value,
                "category": category,
                "confidence": confidence,
                "escalation_needed": escalate,
                "escalation_level": esc_level.value,
                "escalation_reason": esc_reason,
                "kb_articles": len(kb_results)
            }
        }


def run_demo():
    """Demo with sample messages."""
    agent = CustomerSupportAgent()
    
    tests = [
        {"name": "WhatsApp - How-To", "message": "How do I set up recurring tasks?", "channel": "whatsapp", "customer": CustomerProfile(name="Sarah", plan="Business")},
        {"name": "WhatsApp - Billing (Iter 1)", "message": "Charged twice! TXN-98765 and TXN-98766", "channel": "whatsapp", "customer": CustomerProfile(name="James", plan="Professional")},
        {"name": "Web Form - Pricing (Iter 1)", "message": "What are your pricing plans? Nonprofit discount?", "channel": "web_form", "customer": CustomerProfile(name="Emily", plan="Starter")}
    ]
    
    print("=" * 80)
    print("NEXUSFLOW DIGITAL FTE - CORE LOOP v1.1")
    print("Iteration 1: Pricing Query Handling")
    print("=" * 80)
    
    for i, test in enumerate(tests, 1):
        print(f"\n{'='*60}")
        print(f"TEST {i}: {test['name']}")
        print(f"{'='*60}")
        
        result = agent.process_message(test["message"], test["channel"], test["customer"])
        
        print(f"Category: {result['metadata']['category']}")
        print(f"Sentiment: {result['metadata']['sentiment']}, Urgency: {result['metadata']['urgency']}")
        print(f"Escalation: {result['metadata']['escalation_needed']} ({result['metadata']['escalation_level']})")
        print(f"\nResponse:\n{result['response'][:250]}...")


if __name__ == "__main__":
    run_demo()
