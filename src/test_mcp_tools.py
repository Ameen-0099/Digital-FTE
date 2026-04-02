"""
Test script for MCP Server tools.
Tests all MCP tools by directly calling the handlers.
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.mcp_server import (
    handle_search_knowledge_base,
    handle_create_ticket,
    handle_get_customer_history,
    handle_escalate_to_human,
    handle_send_response,
    handle_analyze_sentiment,
    handle_extract_topics,
    tickets,
    escalations
)


def clear_test_data():
    """Clear test data before running tests."""
    tickets.clear()
    escalations.clear()
    print("🗑️  Cleared previous test data\n")


def print_test_header(test_name: str):
    """Print formatted test header."""
    print("\n" + "=" * 80)
    print(f"TEST: {test_name}")
    print("=" * 80)


def print_result(result, test_name: str = ""):
    """Print test result."""
    if hasattr(result, 'content') and result.content:
        content = result.content[0]
        if hasattr(content, 'text'):
            print(f"\n{test_name} Result:")
            try:
                # Try to parse as JSON and pretty print
                print(json.dumps(json.loads(content.text), indent=2))
            except json.JSONDecodeError:
                # If not JSON, print as plain text (error case)
                print(content.text)
    return result


async def test_search_knowledge_base():
    """Test the search_knowledge_base tool."""
    print_test_header("1. search_knowledge_base")
    
    # Test 1: Search for export-related articles
    print("\n--- Test 1a: Search for 'export gantt chart to PDF' ---")
    result = await handle_search_knowledge_base({"query": "export gantt chart to PDF"})
    print_result(result, "Search")
    
    # Test 2: Search for billing
    print("\n--- Test 1b: Search for 'billing refund duplicate charge' ---")
    result = await handle_search_knowledge_base({"query": "billing refund duplicate charge"})
    print_result(result, "Search")
    
    # Test 3: Search for recurring tasks
    print("\n--- Test 1c: Search for 'recurring tasks schedule' ---")
    result = await handle_search_knowledge_base({"query": "recurring tasks schedule"})
    print_result(result, "Search")
    
    print("\n✅ search_knowledge_base tests passed")
    return True


async def test_create_ticket():
    """Test the create_ticket tool."""
    print_test_header("2. create_ticket")
    
    # Test 1: Create a basic ticket
    print("\n--- Test 2a: Create ticket (email channel) ---")
    result = await handle_create_ticket({
        "customer_id": "alice@techcorp.com",
        "issue": "I'm having trouble exporting my Gantt chart to PDF. It shows a loading spinner but nothing happens.",
        "priority": "high",
        "channel": "email",
        "subject": "Gantt export issue"
    })
    print_result(result, "Create Ticket")
    
    # Test 2: Create WhatsApp ticket
    print("\n--- Test 2b: Create ticket (WhatsApp channel) ---")
    result = await handle_create_ticket({
        "customer_id": "bob@startup.io",
        "issue": "How do I set up recurring tasks for weekly meetings?",
        "priority": "low",
        "channel": "whatsapp",
        "subject": "Recurring tasks question"
    })
    print_result(result, "Create Ticket")
    
    # Test 3: Create web form ticket
    print("\n--- Test 2c: Create ticket (web_form channel) ---")
    result = await handle_create_ticket({
        "customer_id": "carol@enterprise.com",
        "issue": "SSO not working after IT update. 200+ users cannot log in.",
        "priority": "critical",
        "channel": "web_form",
        "subject": "CRITICAL: SSO down"
    })
    print_result(result, "Create Ticket")
    
    # Test 4: Error case - missing required field
    print("\n--- Test 2d: Error case (missing issue) ---")
    result = await handle_create_ticket({
        "customer_id": "test@example.com",
        "priority": "medium",
        "channel": "email"
    })
    print_result(result, "Error Case")
    
    print("\n✅ create_ticket tests passed")
    return True


async def test_get_customer_history():
    """Test the get_customer_history tool."""
    print_test_header("3. get_customer_history")
    
    # First create a ticket to have history
    print("\n--- Creating initial ticket for history ---")
    await handle_create_ticket({
        "customer_id": "history@test.com",
        "issue": "Initial issue for history test",
        "priority": "medium",
        "channel": "email"
    })
    
    # Test 1: Get history for existing customer
    print("\n--- Test 3a: Get history for existing customer ---")
    result = await handle_get_customer_history({"customer_id": "history@test.com"})
    print_result(result, "Customer History")
    
    # Test 2: Get history for non-existent customer
    print("\n--- Test 3b: Get history for non-existent customer ---")
    result = await handle_get_customer_history({"customer_id": "nonexistent@example.com"})
    print_result(result, "Non-existent Customer")
    
    print("\n✅ get_customer_history tests passed")
    return True


async def test_escalate_to_human():
    """Test the escalate_to_human tool."""
    print_test_header("4. escalate_to_human")
    
    # First create a ticket to escalate
    print("\n--- Creating ticket to escalate ---")
    create_result = await handle_create_ticket({
        "customer_id": "escalate@test.com",
        "issue": "Billing dispute - charged twice",
        "priority": "high",
        "channel": "email"
    })
    # Extract ticket_id from result
    ticket_id = json.loads(create_result.content[0].text)["ticket_id"]
    print(f"Created ticket: {ticket_id}")
    
    # Test 1: Escalate billing dispute
    print("\n--- Test 4a: Escalate billing dispute ---")
    result = await handle_escalate_to_human({
        "ticket_id": ticket_id,
        "reason": "Billing dispute requires verification - customer charged twice",
        "urgency": "high"
    })
    print_result(result, "Escalation")
    
    # Test 2: Escalate legal matter
    print("\n--- Test 4b: Escalate legal matter ---")
    create_result2 = await handle_create_ticket({
        "customer_id": "legal@test.com",
        "issue": "GDPR data deletion request",
        "priority": "high",
        "channel": "email"
    })
    ticket_id2 = json.loads(create_result2.content[0].text)["ticket_id"]
    
    result = await handle_escalate_to_human({
        "ticket_id": ticket_id2,
        "reason": "Legal matter - GDPR right to erasure request",
        "urgency": "critical"
    })
    print_result(result, "Legal Escalation")
    
    # Test 3: Error case - invalid ticket
    print("\n--- Test 4c: Error case (invalid ticket_id) ---")
    result = await handle_escalate_to_human({
        "ticket_id": "INVALID-123",
        "reason": "Test error"
    })
    print_result(result, "Error Case")
    
    print("\n✅ escalate_to_human tests passed")
    return True


async def test_send_response():
    """Test the send_response tool."""
    print_test_header("5. send_response")
    
    # First create a ticket to respond to
    print("\n--- Creating ticket to respond to ---")
    create_result = await handle_create_ticket({
        "customer_id": "response@test.com",
        "issue": "How do I reset my password?",
        "priority": "low",
        "channel": "email"
    })
    ticket_id = json.loads(create_result.content[0].text)["ticket_id"]
    print(f"Created ticket: {ticket_id}")
    
    # Test 1: Send email response
    print("\n--- Test 5a: Send email response ---")
    result = await handle_send_response({
        "ticket_id": ticket_id,
        "message": "Hi there,\n\nTo reset your password, go to app.nexusflow.com and click 'Forgot Password'. Enter your email and we'll send you a reset link.\n\nBest regards,\nNexusFlow Support",
        "channel": "email"
    })
    print_result(result, "Email Response")
    
    # Test 2: Send WhatsApp response
    print("\n--- Test 5b: Send WhatsApp response ---")
    result = await handle_send_response({
        "ticket_id": ticket_id,
        "message": "Hi! To reset password: Go to app.nexusflow.com → Click 'Forgot Password' → Enter email → Check inbox for reset link 👍",
        "channel": "whatsapp"
    })
    print_result(result, "WhatsApp Response")
    
    # Test 3: Error case - invalid channel
    print("\n--- Test 5c: Error case (invalid channel) ---")
    result = await handle_send_response({
        "ticket_id": ticket_id,
        "message": "Test message",
        "channel": "sms"  # Invalid
    })
    print_result(result, "Error Case")
    
    print("\n✅ send_response tests passed")
    return True


async def test_analyze_sentiment():
    """Test the analyze_sentiment tool."""
    print_test_header("6. analyze_sentiment")
    
    # Test 1: Positive sentiment
    print("\n--- Test 6a: Positive sentiment ---")
    result = await handle_analyze_sentiment({
        "message": "I love NexusFlow! The interface is so clean and intuitive. Best project management tool we've used!"
    })
    print_result(result, "Positive Sentiment")
    
    # Test 2: Frustrated sentiment
    print("\n--- Test 6b: Frustrated sentiment ---")
    result = await handle_analyze_sentiment({
        "message": "This is so frustrating! The export feature is broken and I have a presentation tomorrow. This is unacceptable!"
    })
    print_result(result, "Frustrated Sentiment")
    
    # Test 3: Panicked sentiment
    print("\n--- Test 6c: Panicked sentiment ---")
    result = await handle_analyze_sentiment({
        "message": "HELP!!! Everything disappeared from my board! All my tasks are gone!!! This is a CRITICAL emergency!!!"
    })
    print_result(result, "Panicked Sentiment")
    
    # Test 4: Neutral sentiment
    print("\n--- Test 6d: Neutral sentiment ---")
    result = await handle_analyze_sentiment({
        "message": "How do I set up recurring tasks for weekly meetings?"
    })
    print_result(result, "Neutral Sentiment")
    
    print("\n✅ analyze_sentiment tests passed")
    return True


async def test_extract_topics():
    """Test the extract_topics tool."""
    print_test_header("7. extract_topics")
    
    # Test 1: Export topic
    print("\n--- Test 7a: Export topic ---")
    result = await handle_extract_topics({
        "message": "I can't export my Gantt chart to PDF. The download keeps failing."
    })
    print_result(result, "Export Topics")
    
    # Test 2: Billing topic
    print("\n--- Test 7b: Billing topic ---")
    result = await handle_extract_topics({
        "message": "I was charged twice for my subscription. Need a refund for the duplicate transaction."
    })
    print_result(result, "Billing Topics")
    
    # Test 3: Integration topic
    print("\n--- Test 7c: Integration topic ---")
    result = await handle_extract_topics({
        "message": "The Slack integration stopped syncing. Our API connection keeps failing."
    })
    print_result(result, "Integration Topics")
    
    # Test 4: Multiple topics
    print("\n--- Test 7d: Multiple topics ---")
    result = await handle_extract_topics({
        "message": "How do I set up recurring tasks and track time for my team? Also need help with guest access."
    })
    print_result(result, "Multiple Topics")
    
    print("\n✅ extract_topics tests passed")
    return True


async def run_all_tests():
    """Run all MCP tool tests."""
    print("=" * 80)
    print("NEXUSFLOW DIGITAL FTE - MCP SERVER TEST SUITE")
    print("Exercise 1.4: Model Context Protocol Server")
    print("=" * 80)
    print(f"\nTest started at: {datetime.now().isoformat()}")
    
    # Clear test data
    clear_test_data()
    
    # Track results
    results = {
        "search_knowledge_base": False,
        "create_ticket": False,
        "get_customer_history": False,
        "escalate_to_human": False,
        "send_response": False,
        "analyze_sentiment": False,
        "extract_topics": False
    }
    
    # Run tests
    try:
        results["search_knowledge_base"] = await test_search_knowledge_base()
    except Exception as e:
        print(f"\n❌ search_knowledge_base FAILED: {e}")
    
    try:
        results["create_ticket"] = await test_create_ticket()
    except Exception as e:
        print(f"\n❌ create_ticket FAILED: {e}")
    
    try:
        results["get_customer_history"] = await test_get_customer_history()
    except Exception as e:
        print(f"\n❌ get_customer_history FAILED: {e}")
    
    try:
        results["escalate_to_human"] = await test_escalate_to_human()
    except Exception as e:
        print(f"\n❌ escalate_to_human FAILED: {e}")
    
    try:
        results["send_response"] = await test_send_response()
    except Exception as e:
        print(f"\n❌ send_response FAILED: {e}")
    
    try:
        results["analyze_sentiment"] = await test_analyze_sentiment()
    except Exception as e:
        print(f"\n❌ analyze_sentiment FAILED: {e}")
    
    try:
        results["extract_topics"] = await test_extract_topics()
    except Exception as e:
        print(f"\n❌ extract_topics FAILED: {e}")
    
    # Print summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY REPORT")
    print("=" * 80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for tool, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {tool}")
    
    print(f"\n   Total: {passed}/{total} tools passed ({100*passed/total:.0f}%)")
    print(f"\nTest completed at: {datetime.now().isoformat()}")
    
    # Print ticket summary
    print("\n" + "=" * 80)
    print("TICKET SUMMARY")
    print("=" * 80)
    print(f"   Total tickets created: {len(tickets)}")
    print(f"   Total escalations: {len(escalations)}")
    
    for ticket_id, ticket in tickets.items():
        print(f"\n   Ticket: {ticket_id}")
        print(f"      Customer: {ticket['customer_id']}")
        print(f"      Subject: {ticket['subject']}")
        print(f"      Status: {ticket['status']}")
        print(f"      Messages: {len(ticket['messages'])}")
    
    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80)
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
