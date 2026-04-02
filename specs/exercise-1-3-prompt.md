# Exercise 1.3: All Done - Integration & Testing (4-5 hours)

## Overview

Now that you have a working core loop prototype, it's time to integrate everything together, add PostgreSQL CRM storage, run comprehensive tests, and prepare for the next phase.

---

## Task 1: PostgreSQL CRM Integration (2 hours)

### Create Database Schema

Create `src/database/schema.sql` with the following tables:

```sql
-- Customers table
CREATE TABLE customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    phone VARCHAR(50),
    company VARCHAR(255),
    plan VARCHAR(50) DEFAULT 'Free',
    account_age_days INTEGER DEFAULT 0,
    is_vip BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Conversations table
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES customers(id),
    channel VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'open',
    sentiment VARCHAR(50),
    urgency VARCHAR(50),
    category VARCHAR(100),
    escalation_level VARCHAR(50),
    escalation_reason TEXT,
    confidence_score DECIMAL(3,2),
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    first_response_at TIMESTAMP,
    resolved_at TIMESTAMP,
    sla_deadline TIMESTAMP
);

-- Messages table
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id),
    direction VARCHAR(10) NOT NULL, -- 'inbound' or 'outbound'
    content TEXT NOT NULL,
    sentiment_score DECIMAL(3,2),
    ai_generated BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tickets table (denormalized for quick reporting)
CREATE TABLE tickets (
    id VARCHAR(50) PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id),
    customer_id UUID REFERENCES customers(id),
    channel VARCHAR(50),
    subject VARCHAR(500),
    message TEXT,
    response TEXT,
    sentiment VARCHAR(50),
    urgency VARCHAR(50),
    category VARCHAR(100),
    escalation_level VARCHAR(50),
    status VARCHAR(50) DEFAULT 'open',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_conversations_customer ON conversations(customer_id);
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE INDEX idx_tickets_customer ON tickets(customer_id);
CREATE INDEX idx_tickets_created ON tickets(created_at);
CREATE INDEX idx_tickets_category ON tickets(category);
```

### Create Database Connection Module

Create `src/database/db_connection.py`:

```python
"""
PostgreSQL Database Connection Module
Handles all database operations for the Digital FTE
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, List, Dict
from contextlib import contextmanager

class DatabaseConnection:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database cursors"""
        conn = psycopg2.connect(self.connection_string)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                yield cur
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def save_customer(self, customer_data: Dict) -> str:
        """Save or update customer, return customer_id"""
        # Implement upsert logic
        pass
    
    def create_conversation(self, conversation_data: Dict) -> str:
        """Create new conversation record"""
        pass
    
    def save_message(self, message_data: Dict) -> str:
        """Save message to conversation"""
        pass
    
    def create_ticket(self, ticket_data: Dict) -> str:
        """Create ticket record"""
        pass
    
    def get_customer_history(self, customer_email: str) -> List[Dict]:
        """Get customer's conversation history"""
        pass
    
    def get_metrics(self, days: int = 30) -> Dict:
        """Get support metrics for reporting"""
        pass
```

### Integrate Database with Core Loop

Update `src/agent/core_loop.py` to:
1. Accept database connection in constructor
2. Save customers on first interaction
3. Create conversation records
4. Save all messages (inbound and outbound)
5. Create ticket records
6. Update conversation status on resolution

---

## Task 2: Comprehensive Testing (1.5 hours)

### Create Test Suite

Create `tests/test_core_loop.py` with tests for:

```python
"""
Comprehensive Test Suite for Digital FTE
"""

import pytest
from src.agent.core_loop import CustomerSupportAgent, CustomerProfile
from src.database.db_connection import DatabaseConnection

class TestSentimentAnalysis:
    def test_positive_sentiment(self):
        pass
    
    def test_frustrated_sentiment(self):
        pass
    
    def test_panicked_sentiment(self):
        pass
    
    def test_billing_concern(self):
        pass

class TestIntentClassification:
    def test_how_to_intent(self):
        pass
    
    def test_billing_dispute_intent(self):
        pass
    
    def test_pricing_inquiry_intent(self):
        pass
    
    def test_technical_issue_intent(self):
        pass

class TestEscalation:
    def test_explicit_human_request(self):
        pass
    
    def test_billing_dispute_escalation(self):
        pass
    
    def test_vip_sentiment_escalation(self):
        pass
    
    def test_panic_escalation(self):
        pass

class TestResponseGeneration:
    def test_email_format(self):
        pass
    
    def test_whatsapp_length(self):
        pass
    
    def test_webform_format(self):
        pass

class TestDatabaseIntegration:
    def test_customer_save(self):
        pass
    
    def test_conversation_creation(self):
        pass
    
    def test_ticket_creation(self):
        pass
    
    def test_customer_history(self):
        pass

class TestEndToEnd:
    def test_simple_how_to_flow(self):
        pass
    
    def test_billing_dispute_flow(self):
        pass
    
    def test_escalation_flow(self):
        pass
```

### Run Tests Against All 55 Sample Tickets

Create `tests/test_all_tickets.py`:

```python
"""
Run core loop against all 55 sample tickets from sample-tickets.json
Generate accuracy report
"""

import json
from src.agent.core_loop import CustomerSupportAgent, CustomerProfile

def test_all_tickets():
    with open('context/sample-tickets.json') as f:
        data = json.load(f)
    
    agent = CustomerSupportAgent()
    results = []
    
    for ticket in data['tickets']:
        result = agent.process_message(
            message=ticket['message'],
            channel=ticket['channel'],
            customer=CustomerProfile(
                name=ticket['customer']['name'],
                company=ticket['customer']['company'],
                plan=ticket['customer']['plan']
            ),
            subject=ticket.get('subject')
        )
        
        # Compare with expected values
        results.append({
            'ticket_id': ticket['id'],
            'expected_sentiment': ticket['sentiment'],
            'actual_sentiment': result['metadata']['sentiment'],
            'expected_urgency': ticket['urgency'],
            'actual_urgency': result['metadata']['urgency'],
            'expected_category': ticket['category'],
            'actual_category': result['metadata']['category'],
            'expected_escalation': ticket['resolution_status'] == 'escalated',
            'actual_escalation': result['metadata']['escalation_needed']
        })
    
    # Generate report
    generate_accuracy_report(results)
```

### Generate Accuracy Report

Create `specs/accuracy-report.md` with:
- Overall sentiment accuracy %
- Overall urgency accuracy %
- Overall category accuracy %
- Escalation accuracy %
- Breakdown by channel
- Breakdown by category
- Top 10 misclassifications with analysis

---

## Task 3: Daily Sentiment Report Generator (1 hour)

### Create Report Module

Create `src/reports/daily_sentiment_report.py`:

```python
"""
Daily Sentiment Report Generator
Generates daily summary of customer sentiment and support metrics
"""

from datetime import datetime, timedelta
from typing import Dict, List
from src.database.db_connection import DatabaseConnection

class DailySentimentReport:
    def __init__(self, db: DatabaseConnection):
        self.db = db
    
    def generate_report(self, date: datetime = None) -> Dict:
        """
        Generate daily sentiment report with:
        - Total tickets
        - Sentiment distribution
        - Urgency distribution
        - Category breakdown
        - Channel breakdown
        - Average resolution time
        - Escalation rate
        - Top issues
        - Sentiment trend vs previous day
        """
        pass
    
    def format_report_email(self, report: Dict) -> str:
        """Format report as email for stakeholders"""
        pass
    
    def send_report(self, recipients: List[str], report: Dict):
        """Send report via email"""
        pass
```

### Sample Report Output

```markdown
# Daily Sentiment Report - March 27, 2026

## Summary
- Total Tickets: 47
- Resolved by AI: 32 (68%)
- Escalated to Human: 15 (32%)
- Average Response Time: 1.2 minutes
- Average Resolution Time: 3.4 hours

## Sentiment Distribution
| Sentiment | Count | Percentage |
|-----------|-------|------------|
| Very Positive | 5 | 10.6% |
| Positive | 8 | 17.0% |
| Neutral | 18 | 38.3% |
| Concerned | 6 | 12.8% |
| Frustrated | 7 | 14.9% |
| Very Frustrated | 2 | 4.3% |
| Panicked | 1 | 2.1% |

## Top Categories
1. How-To: 15 tickets (32%)
2. Technical Issue: 8 tickets (17%)
3. Billing Inquiry: 7 tickets (15%)
4. Pricing Inquiry: 6 tickets (13%)
5. Integration: 5 tickets (11%)

## Channel Breakdown
- Email: 22 tickets (47%)
- WhatsApp: 14 tickets (30%)
- Web Form: 11 tickets (23%)

## Escalations
- Total: 15 (32%)
- Billing Disputes: 5
- Technical Issues: 4
- VIP Customers: 3
- Low Confidence: 2
- Other: 1

## Sentiment Trend
- Positive sentiment: +5% vs yesterday
- Negative sentiment: -2% vs yesterday
- AI resolution rate: +3% vs yesterday

## Action Items
1. Review billing dispute pattern (5 escalations today)
2. Update knowledge base for Gantt export issues
3. Follow up with 3 VIP customers who were frustrated
```

---

## Task 4: Final Documentation (30 minutes)

### Update Discovery Log

Add to `specs/discovery-log.md`:
- Implementation decisions made
- Deviations from initial plan
- Lessons learned
- Technical debt identified

### Create README

Create `README.md`:

```markdown
# NexusFlow Customer Success Digital FTE

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- pip dependencies (see requirements.txt)

### Installation
```bash
pip install -r requirements.txt
```

### Configuration
```bash
# Set environment variables
export DATABASE_URL="postgresql://user:pass@localhost:5432/nexusflow_crm"
export OPENAI_API_KEY="your-key-here"
```

### Run Database Migrations
```bash
psql $DATABASE_URL < src/database/schema.sql
```

### Run the Agent
```bash
python src/agent/core_loop.py
```

### Run Tests
```bash
pytest tests/ -v
```

### Generate Daily Report
```bash
python src/reports/daily_sentiment_report.py
```

## Project Structure
[Show tree structure]

## Architecture
[Include architecture diagram]

## API Reference
[Document main classes and methods]

## Contributing
[Guidelines for contributions]

## License
[Your license]
```

---

## Deliverables Checklist

- [ ] `src/database/schema.sql` - Database schema
- [ ] `src/database/db_connection.py` - Database module
- [ ] `src/agent/core_loop.py` - Updated with DB integration
- [ ] `tests/test_core_loop.py` - Unit tests
- [ ] `tests/test_all_tickets.py` - Integration tests
- [ ] `specs/accuracy-report.md` - Test accuracy report
- [ ] `src/reports/daily_sentiment_report.py` - Report generator
- [ ] `README.md` - Project documentation
- [ ] `requirements.txt` - Python dependencies

---

## Success Criteria

### Must Have (Pass)
- [ ] All 5 database tables created and working
- [ ] Core loop saves data to PostgreSQL
- [ ] 20+ unit tests passing
- [ ] Test run against all 55 sample tickets
- [ ] Accuracy report generated
- [ ] Daily sentiment report generates valid output
- [ ] README with setup instructions

### Should Have (Good)
- [ ] 70%+ sentiment accuracy on test tickets
- [ ] 80%+ escalation accuracy
- [ ] Channel-specific response formatting working
- [ ] Customer history retrieval working
- [ ] Report email formatting works

### Nice to Have (Excellent)
- [ ] 85%+ sentiment accuracy
- [ ] 90%+ escalation accuracy
- [ ] Automated test CI/CD pipeline
- [ ] Dashboard for metrics visualization
- [ ] Performance benchmarks

---

## Time Allocation

| Task | Estimated Time | Priority |
|------|----------------|----------|
| Database Schema & Connection | 1 hour | Must Have |
| Core Loop DB Integration | 1 hour | Must Have |
| Unit Tests | 1 hour | Must Have |
| Integration Tests (55 tickets) | 30 min | Must Have |
| Accuracy Report | 30 min | Must Have |
| Daily Report Generator | 1 hour | Should Have |
| Documentation (README) | 30 min | Must Have |
| Buffer/Debugging | 1 hour | - |
| **Total** | **5.5 hours** | - |

---

## Next Steps After Exercise 1.3

Once Exercise 1.3 is complete, you will have:
1. ✅ A working core loop prototype
2. ✅ PostgreSQL CRM with full data persistence
3. ✅ Comprehensive test suite with accuracy metrics
4. ✅ Daily sentiment reporting
5. ✅ Complete documentation

This sets the foundation for:
- **Exercise 2.1**: Gmail Integration
- **Exercise 2.2**: WhatsApp Business API Integration
- **Exercise 2.3**: Web Form Widget
- **Exercise 3.1**: Advanced AI/ML Improvements
- **Exercise 3.2**: Dashboard & Analytics
- **Exercise 3.3**: Production Deployment

---

## Submission Instructions

When complete:
1. Push all code to GitHub
2. Ensure README is complete
3. Include accuracy report in specs/
4. Record demo video (3-5 minutes) showing:
   - Processing a message
   - Database records created
   - Daily report generation
5. Submit via hackathon portal

Good luck! 🚀
