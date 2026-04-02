"""
Test script for core_loop.py prototype.
Tests against 5 sample tickets from sample-tickets.json.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core_loop_v1_1 import (
    CustomerSupportAgent, 
    CustomerProfile,
    run_demo
)


def load_sample_tickets():
    """Load sample tickets from JSON file."""
    # Navigate from src/agent to context folder
    tickets_path = Path(__file__).parent.parent.parent / "context" / "sample-tickets.json"
    with open(tickets_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data["tickets"]


def create_customer_from_ticket(ticket_data):
    """Create CustomerProfile from ticket data."""
    return CustomerProfile(
        name=ticket_data["customer"]["name"],
        email=ticket_data["customer"].get("email"),
        phone=ticket_data["customer"].get("phone"),
        company=ticket_data["customer"]["company"],
        plan=ticket_data["customer"]["plan"],
        account_age_days=ticket_data["customer"].get("account_age_days", 0),
        is_vip=ticket_data["customer"]["plan"] == "Enterprise"
    )


def run_ticket_test(agent, ticket_data, test_number):
    """Run a single ticket through the agent."""
    print("\n" + "=" * 80)
    print(f"TEST {test_number}: {ticket_data['id']}")
    print("=" * 80)
    
    # Print input details
    print(f"\n📥 INPUT:")
    print(f"   Channel: {ticket_data['channel']}")
    print(f"   Customer: {ticket_data['customer']['name']}")
    print(f"   Company: {ticket_data['customer']['company']}")
    print(f"   Plan: {ticket_data['customer']['plan']}")
    print(f"   Subject: {ticket_data.get('subject', 'N/A')}")
    print(f"   Message Preview: {ticket_data['message'][:100]}...")
    print(f"\n   [Expected] Sentiment: {ticket_data['sentiment']}, Urgency: {ticket_data['urgency']}, Category: {ticket_data['category']}")
    
    # Create customer profile
    customer = create_customer_from_ticket(ticket_data)
    
    # Process through agent
    result = agent.process_message(
        message=ticket_data["message"],
        channel=ticket_data["channel"],
        customer=customer,
        subject=ticket_data.get("subject")
    )
    
    # Print output details
    print(f"\n📤 OUTPUT:")
    print(f"   Sentiment: {result['metadata']['sentiment']} (expected: {ticket_data['sentiment']})")
    print(f"   Urgency: {result['metadata']['urgency']} (expected: {ticket_data['urgency']})")
    print(f"   Category: {result['metadata']['category']} (expected: {ticket_data['category']})")
    print(f"   Confidence: {result['metadata']['confidence']:.2f}")
    print(f"   Escalation Needed: {result['metadata'].get('escalation_needed', 'N/A')}")
    print(f"   Escalation Level: {result['metadata']['escalation_level']}")
    print(f"   Escalation Reason: {result['metadata']['escalation_reason']}")
    print(f"   KB Articles Found: {result['metadata'].get('knowledge_articles_found', result['metadata'].get('kb_results_count', 'N/A'))}")
    
    # Print response
    print(f"\n💬 RESPONSE ({len(result['response'])} chars):")
    print("-" * 40)
    print(result['response'])
    print("-" * 40)
    
    # Print ticket info
    print(f"\n🎫 TICKET:")
    print(f"   ID: {result['ticket']['ticket_id']}")
    print(f"   Status: {result['ticket']['status']}")
    print(f"   Channel: {result['ticket']['channel']}")
    
    # Simple accuracy check
    sentiment_match = result['metadata']['sentiment'] == ticket_data['sentiment']
    urgency_match = result['metadata']['urgency'] == ticket_data['urgency']
    
    print(f"\n✅ ACCURACY CHECK:")
    print(f"   Sentiment Match: {'✓' if sentiment_match else '✗'}")
    print(f"   Urgency Match: {'✓' if urgency_match else '✗'}")
    
    return result


def main():
    """Run tests against 5 sample tickets."""
    print("=" * 80)
    print("NEXUSFLOW DIGITAL FTE - CORE LOOP PROTOTYPE TESTS")
    print("Exercise 1.2 - Testing Against Sample Tickets")
    print("=" * 80)
    
    # Load tickets
    tickets = load_sample_tickets()
    
    # Select 5 diverse tickets
    # Mix of channels: email, whatsapp, web_form
    # Mix of complexity: simple how-to, technical issue, billing, escalation-needed
    selected_indices = [1, 2, 4, 7, 14]  # TKT-002, TKT-003, TKT-005, TKT-008, TKT-015
    
    test_tickets = [tickets[i] for i in selected_indices]
    
    print(f"\nSelected {len(test_tickets)} tickets for testing:")
    for i, t in enumerate(test_tickets, 1):
        print(f"  {i}. {t['id']} - {t['channel']} - {t['category']} - {t['sentiment']}")
    
    # Create agent
    agent = CustomerSupportAgent()
    
    # Run tests
    results = []
    for i, ticket in enumerate(test_tickets, 1):
        result = run_ticket_test(agent, ticket, i)
        results.append(result)
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    sentiment_matches = sum(
        1 for r, t in zip(results, test_tickets) 
        if r['metadata']['sentiment'] == t['sentiment']
    )
    urgency_matches = sum(
        1 for r, t in zip(results, test_tickets) 
        if r['metadata']['urgency'] == t['urgency']
    )
    escalations = sum(1 for r in results if r['metadata']['escalation_needed'])
    
    print(f"\nTotal Tests: {len(results)}")
    print(f"Sentiment Accuracy: {sentiment_matches}/{len(results)} ({100*sentiment_matches/len(results):.0f}%)")
    print(f"Urgency Accuracy: {urgency_matches}/{len(results)} ({100*urgency_matches/len(results):.0f}%)")
    print(f"Escalations Triggered: {escalations}/{len(results)}")
    
    print("\n" + "=" * 80)
    print("INITIAL PROTOTYPE TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
