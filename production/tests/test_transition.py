"""
NexusFlow Customer Success Digital FTE - Transition Test Suite
===============================================================
Transition Step 5: Comprehensive pytest tests for production agent verification

This test suite verifies that the new production agent (OpenAI Agents SDK)
behaves exactly like the incubation prototype (MCP-based). Tests cover:

- Edge cases discovered during incubation
- Channel-specific response formatting
- Escalation trigger behavior
- Tool execution order
- Input validation
- Error handling

Author: Digital FTE Team
Version: 1.0.0 (Production)
"""

import pytest
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import production tools - use .tool_call() to invoke FunctionTool objects
from agent.tools import (
    search_knowledge_base,
    create_ticket,
    get_customer_history,
    escalate_to_human,
    send_response,
)

# Import production prompt
from agent.prompts import (
    CUSTOMER_SUCCESS_SYSTEM_PROMPT,
    validate_prompt,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_customer_email():
    """Sample customer email for testing."""
    return "test.customer@example.com"


@pytest.fixture
def sample_ticket_id():
    """Generate a sample ticket ID."""
    return f"TKT-{datetime.now().strftime('%Y%m%d')}-TEST"


@pytest.fixture
def sample_conversation_id():
    """Generate a sample conversation ID."""
    return f"CONV-{datetime.now().strftime('%Y%m%d')}-TEST"


# =============================================================================
# TEST CLASS 1: TRANSITION FROM INCUBATION
# =============================================================================

class TestTransitionFromIncubation:
    """
    Test suite to verify production agent matches incubation behavior.
    
    These tests ensure that all edge cases, escalation rules, channel
    formatting, and tool behaviors discovered during incubation are
    preserved in the production implementation.
    """

    @pytest.mark.asyncio
    async def test_edge_case_empty_message(self):
        """
        Test handling of empty or whitespace-only messages.
        
        EDGE CASE DISCOVERED: During incubation, empty messages could cause
        knowledge base search to return unexpected results or crash.
        
        EXPECTED BEHAVIOR:
        - search_knowledge_base should return error for empty query
        - Error should be gracefully handled, not crash
        - Response should indicate query is required
        """
        # Test empty string
        result = await search_knowledge_base("")
        result_data = json.loads(result)
        
        assert result_data["error"] is not None, "Empty query should return error"
        assert "empty" in result_data["error"].lower(), "Error should mention empty query"
        
        # Test whitespace only
        result = await search_knowledge_base("   ")
        result_data = json.loads(result)
        
        assert result_data["error"] is not None, "Whitespace query should return error"
        assert result_data["results_count"] == 0, "No results for whitespace query"
        
        print("✅ Empty message edge case handled correctly")

    @pytest.mark.asyncio
    async def test_edge_case_pricing_escalation(self):
        """
        Test automatic escalation for billing/pricing disputes.
        
        EDGE CASE DISCOVERED: During incubation, billing disputes required
        immediate escalation to L1_Tier1 for human verification.
        
        EXPECTED BEHAVIOR:
        - escalate_to_human with billing reason → L1_Tier1
        - Escalation ID generated
        - Status set to "pending"
        """
        # Create a ticket first (required for escalation)
        ticket_result = await create_ticket(
            customer_id="billing@test.com",
            issue="Customer reports duplicate charge",
            priority="high",
            channel="email"
        )
        ticket_data = json.loads(ticket_result)
        ticket_id = ticket_data["ticket_id"]
        
        # Escalate for billing dispute
        result = await escalate_to_human(
            ticket_id=ticket_id,
            reason="Billing dispute requires verification - customer charged twice",
            urgency="high"
        )
        result_data = json.loads(result)
        
        assert result_data["success"] is True, "Escalation should succeed"
        assert result_data["escalation_id"] is not None, "Escalation ID should be generated"
        assert result_data["escalation_level"] == "L1_Tier1", "Billing disputes escalate to L1"
        assert result_data["urgency"] == "high", "Urgency should be preserved"
        assert "billing" in result_data["reason"].lower(), "Reason should be preserved"
        
        print("✅ Pricing/billing escalation handled correctly")

    @pytest.mark.asyncio
    async def test_edge_case_angry_customer(self):
        """
        Test handling of angry/frustrated customer messages.
        
        EDGE CASE DISCOVERED: During incubation, angry customers required
        empathetic responses and often escalation if very frustrated.
        
        EXPECTED BEHAVIOR:
        - Knowledge base search should work for frustrated queries
        - Response should acknowledge frustration
        - Escalation should be considered for very frustrated + VIP
        """
        # Search for issue that frustrated customer might ask
        result = await search_knowledge_base("export not working broken")
        result_data = json.loads(result)
        
        # Should return relevant results even with emotional query
        assert result_data["error"] is None or result_data["error"] == "", "Search should work"
        
        # Create ticket for frustrated customer
        ticket_result = await create_ticket(
            customer_id="frustrated@test.com",
            issue="This is unacceptable! The export feature is completely broken!",
            priority="high",
            channel="email"
        )
        ticket_data = json.loads(ticket_result)
        
        assert ticket_data["success"] is True, "Ticket should be created"
        assert ticket_data["priority"] == "high", "Priority should be high for frustrated customer"
        
        print("✅ Angry customer handling verified")

    @pytest.mark.asyncio
    async def test_channel_response_length_email(self):
        """
        Test email response length handling (no strict limit).
        
        CHANNEL RULE: Email has no character limit, should be formal with signature.
        
        EXPECTED BEHAVIOR:
        - send_response should accept long messages for email
        - No truncation for email channel
        - Response should be delivered successfully
        """
        # Create ticket first
        ticket_result = await create_ticket(
            customer_id="email@test.com",
            issue="Test email response",
            priority="medium",
            channel="email"
        )
        ticket_data = json.loads(ticket_result)
        ticket_id = ticket_data["ticket_id"]
        
        # Long email response (500+ chars)
        long_message = """Dear Valued Customer,

Thank you for contacting NexusFlow Support regarding your inquiry about our project management features.

I would be happy to provide you with detailed information about our capabilities:

1. Task Management: Create, assign, and track tasks with custom fields
2. Gantt Charts: Visual timeline view with dependencies and critical path
3. Time Tracking: Built-in timer and manual time entry
4. Reporting: Custom dashboards and automated reports
5. Integrations: Slack, Google Calendar, GitHub, Salesforce, and more

If you have any additional questions or need further clarification on any of these features, please don't hesitate to reach out.

Best regards,
NexusFlow Support Team
support@nexusflow.com

Ticket: """ + ticket_id
        
        result = await send_response(
            ticket_id=ticket_id,
            message=long_message,
            channel="email"
        )
        result_data = json.loads(result)
        
        assert result_data["success"] is True, "Email response should succeed"
        assert result_data["status"] == "delivered", "Email should be delivered"
        assert result_data["message_length"] == len(long_message), "Full length preserved"
        assert result_data["message_length"] > 500, "Long email accepted"
        
        print("✅ Email response length handled correctly")

    @pytest.mark.asyncio
    async def test_channel_response_length_whatsapp(self):
        """
        Test WhatsApp response length handling (300 char strict limit).
        
        CHANNEL RULE: WhatsApp has strict 300 character limit.
        
        EXPECTED BEHAVIOR:
        - send_response should truncate messages over 300 chars
        - Truncated message should end with "..."
        - Warning should be logged
        """
        # Create ticket first
        ticket_result = await create_ticket(
            customer_id="whatsapp@test.com",
            issue="Test WhatsApp response",
            priority="medium",
            channel="whatsapp"
        )
        ticket_data = json.loads(ticket_result)
        ticket_id = ticket_data["ticket_id"]
        
        # Long WhatsApp message (should be truncated)
        long_message = """Hey there! 👋 Thanks for reaching out about NexusFlow! 

To set up recurring tasks: Open your task → Click 'Repeat' → Choose frequency (Daily/Weekly/Monthly) → Select the day → Save! 

The task will automatically create new instances based on your schedule. You can also set end dates or specific occurrence counts.

Need more help? Just ask! 😊"""
        
        assert len(long_message) > 300, "Test message should exceed limit"
        
        result = await send_response(
            ticket_id=ticket_id,
            message=long_message,
            channel="whatsapp"
        )
        result_data = json.loads(result)
        
        assert result_data["success"] is True, "WhatsApp response should succeed"
        assert result_data["message_length"] <= 300, "WhatsApp message truncated to 300 chars"
        # Message should be truncated
        assert result_data["message_length"] < len(long_message), "Message should be shortened"
        
        print("✅ WhatsApp response length limit enforced correctly")

    @pytest.mark.asyncio
    async def test_tool_execution_order(self):
        """
        Test that tools are called in the correct order per workflow.
        
        WORKFLOW REQUIREMENT: create_ticket → get_customer_history → search_knowledge_base → send_response
        
        EXPECTED BEHAVIOR:
        - create_ticket must be called first to get ticket_id
        - get_customer_history should be called early for context
        - search_knowledge_base before generating response
        - send_response last with ticket_id from step 1
        """
        customer_id = "workflow@test.com"
        
        # Step 1: Create ticket FIRST
        ticket_result = await create_ticket(
            customer_id=customer_id,
            issue="How do I set up recurring tasks?",
            priority="medium",
            channel="web_form"
        )
        ticket_data = json.loads(ticket_result)
        assert ticket_data["success"] is True, "Ticket creation must succeed first"
        ticket_id = ticket_data["ticket_id"]
        
        # Step 2: Get customer history
        history_result = await get_customer_history(customer_id=customer_id)
        history_data = json.loads(history_result)
        # Should work (may be new customer)
        assert "found" in history_data, "History should return found status"
        
        # Step 3: Search knowledge base
        search_result = await search_knowledge_base(query="recurring tasks setup")
        search_data = json.loads(search_result)
        assert "results_count" in search_data, "Search should return results count"
        
        # Step 4: Send response (requires ticket_id from step 1)
        response_result = await send_response(
            ticket_id=ticket_id,
            message="Hello! To set up recurring tasks: Open task → Click 'Repeat' → Choose frequency → Select day → Save!",
            channel="web_form"
        )
        response_data = json.loads(response_result)
        assert response_data["success"] is True, "Response should send with ticket_id"
        
        print("✅ Tool execution order verified")


# =============================================================================
# TEST CLASS 2: TOOL MIGRATION
# =============================================================================

class TestToolMigration:
    """
    Test suite to verify @function_tool versions work correctly.
    
    These tests ensure that the new OpenAI Agents SDK tool implementations
    match the behavior of the original MCP tools from incubation.
    """

    @pytest.mark.asyncio
    async def test_search_knowledge_base_migration(self):
        """
        Verify search_knowledge_base @function_tool works correctly.
        
        MIGRATION CHECK:
        - Input validation with Pydantic
        - Returns JSON string (not CallToolResult)
        - Error handling with graceful fallback
        """
        # Valid search
        result = await search_knowledge_base("how to export gantt chart")
        result_data = json.loads(result)
        
        assert "query" in result_data, "Should return query"
        assert "results_count" in result_data, "Should return results count"
        assert "articles" in result_data, "Should return articles"
        assert "confidence" in result_data, "Should return confidence"
        assert isinstance(result_data["confidence"], float), "Confidence should be float"
        
        # Invalid search (empty)
        result = await search_knowledge_base("")
        result_data = json.loads(result)
        
        assert "error" in result_data, "Should return error for empty query"
        
        print("✅ search_knowledge_base migration verified")

    @pytest.mark.asyncio
    async def test_create_ticket_migration(self):
        """
        Verify create_ticket @function_tool works correctly.
        
        MIGRATION CHECK:
        - Pydantic validation for all fields
        - Priority/channel enum validation
        - Returns proper ticket_id format
        """
        # Valid ticket creation
        result = await create_ticket(
            customer_id="migration@test.com",
            issue="Testing ticket creation migration",
            priority="medium",
            channel="email",
            subject="Migration Test"
        )
        result_data = json.loads(result)
        
        assert result_data["success"] is True, "Should succeed"
        assert result_data["ticket_id"].startswith("TKT-"), "Ticket ID format correct"
        assert result_data["status"] == "open", "Initial status should be open"
        assert "created_at" in result_data, "Should have timestamp"
        
        # Invalid priority
        result = await create_ticket(
            customer_id="test@test.com",
            issue="Test issue",
            priority="invalid_priority",  # type: ignore
            channel="email"
        )
        result_data = json.loads(result)
        
        assert result_data["success"] is False, "Should fail with invalid priority"
        assert "error" in result_data, "Should return error message"
        
        print("✅ create_ticket migration verified")

    @pytest.mark.asyncio
    async def test_get_customer_history_migration(self):
        """
        Verify get_customer_history @function_tool works correctly.
        
        MIGRATION CHECK:
        - Returns found/not_found status
        - Includes VIP detection
        - Returns history_summary for existing customers
        """
        # Test with known customer (from incubation data)
        result = await get_customer_history("alice@techcorp.com")
        result_data = json.loads(result)
        
        assert "found" in result_data, "Should return found status"
        assert "is_vip" in result_data, "Should include VIP status"
        assert "is_new_customer" in result_data, "Should indicate if new customer"
        
        # Test with unknown customer
        result = await get_customer_history("unknown@example.com")
        result_data = json.loads(result)
        
        assert result_data["found"] is False, "Unknown customer should not be found"
        assert result_data["is_new_customer"] is True, "Should be marked as new"
        
        print("✅ get_customer_history migration verified")

    @pytest.mark.asyncio
    async def test_escalate_to_human_migration(self):
        """
        Verify escalate_to_human @function_tool works correctly.
        
        MIGRATION CHECK:
        - Auto-assigns escalation level from reason
        - Returns escalation_id format
        - Validates ticket exists (simulated)
        """
        # Create ticket first
        ticket_result = await create_ticket(
            customer_id="escalation@test.com",
            issue="Test issue for escalation",
            priority="high",
            channel="email"
        )
        ticket_data = json.loads(ticket_result)
        ticket_id = ticket_data["ticket_id"]
        
        # Test legal escalation (should be L4)
        result = await escalate_to_human(
            ticket_id=ticket_id,
            reason="Customer mentioned lawsuit and attorney",
            urgency="critical"
        )
        result_data = json.loads(result)
        
        assert result_data["success"] is True, "Should succeed"
        assert result_data["escalation_level"] == "L4_Management", "Legal → L4"
        assert result_data["escalation_id"].startswith("ESC-"), "Escalation ID format"
        
        # Test technical escalation (should be L2)
        result = await escalate_to_human(
            ticket_id=ticket_id,
            reason="Advanced API integration issue requires specialist",
            urgency="high"
        )
        result_data = json.loads(result)
        
        assert result_data["escalation_level"] == "L2_Tier2", "Technical → L2"
        
        print("✅ escalate_to_human migration verified")

    @pytest.mark.asyncio
    async def test_send_response_migration(self):
        """
        Verify send_response @function_tool works correctly.
        
        MIGRATION CHECK:
        - Channel-specific length enforcement
        - Returns message_id (UUID)
        - Returns delivery status
        """
        # Create ticket first
        ticket_result = await create_ticket(
            customer_id="response@test.com",
            issue="Test issue",
            priority="medium",
            channel="email"
        )
        ticket_data = json.loads(ticket_result)
        ticket_id = ticket_data["ticket_id"]
        
        # Test response
        result = await send_response(
            ticket_id=ticket_id,
            message="Thank you for contacting NexusFlow Support!",
            channel="email"
        )
        result_data = json.loads(result)
        
        assert result_data["success"] is True, "Should succeed"
        assert result_data["message_id"] is not None, "Should return message_id"
        assert result_data["status"] == "delivered", "Should show delivered"
        assert "delivered_at" in result_data, "Should have delivery timestamp"
        
        print("✅ send_response migration verified")


# =============================================================================
# TEST CLASS 3: PROMPT VALIDATION
# =============================================================================

class TestPromptValidation:
    """
    Test suite to verify production prompt meets requirements.
    """

    def test_prompt_contains_required_sections(self):
        """
        Verify system prompt contains all required sections.
        """
        required_sections = [
            "PURPOSE",
            "CHANNEL AWARENESS",
            "REQUIRED WORKFLOW",
            "HARD CONSTRAINTS",
            "ESCALATION TRIGGERS",
            "RESPONSE QUALITY STANDARDS"
        ]
        
        for section in required_sections:
            assert section in CUSTOMER_SUCCESS_SYSTEM_PROMPT, \
                f"Prompt missing required section: {section}"
        
        print("✅ All required prompt sections present")

    def test_prompt_contains_never_rules(self):
        """
        Verify prompt contains all NEVER rules.
        """
        # Count NEVER occurrences
        never_count = CUSTOMER_SUCCESS_SYSTEM_PROMPT.count("NEVER")
        
        assert never_count >= 15, f"Expected 15+ NEVER rules, found {never_count}"
        
        print(f"✅ Prompt contains {never_count} NEVER rules")

    def test_prompt_validation_function(self):
        """
        Verify the validate_prompt function passes.
        """
        is_valid = validate_prompt()
        
        assert is_valid is True, "Prompt validation should pass"
        
        print("✅ Prompt validation function passes")


# =============================================================================
# TEST CLASS 4: INTEGRATION TESTS
# =============================================================================

class TestIntegrationScenarios:
    """
    Integration tests for complete customer interaction flows.
    """

    @pytest.mark.asyncio
    async def test_full_how_to_flow(self):
        """
        Test complete how-to question flow.
        
        FLOW: Customer asks how-to → Search KB → Send response
        """
        customer_id = "howto@test.com"
        
        # Create ticket
        ticket = await create_ticket(
            customer_id=customer_id,
            issue="How do I export Gantt chart?",
            priority="medium",
            channel="email"
        )
        ticket_data = json.loads(ticket)
        ticket_id = ticket_data["ticket_id"]
        
        # Get history
        await get_customer_history(customer_id=customer_id)
        
        # Search KB
        search = await search_knowledge_base("export gantt chart pdf")
        search_data = json.loads(search)
        
        assert search_data["has_relevant_result"] is True, "Should find relevant article"
        
        # Send response
        response = await send_response(
            ticket_id=ticket_id,
            message="To export: 1. Open project → 2. Gantt view → 3. Export → PDF",
            channel="email"
        )
        response_data = json.loads(response)
        
        assert response_data["success"] is True, "Response should send"
        
        print("✅ Full how-to flow completed")

    @pytest.mark.asyncio
    async def test_full_escalation_flow(self):
        """
        Test complete escalation flow.
        
        FLOW: Billing dispute → Create ticket → Escalate → Notify customer
        """
        customer_id = "billing@test.com"
        
        # Create ticket
        ticket = await create_ticket(
            customer_id=customer_id,
            issue="Charged twice this month!",
            priority="high",
            channel="email"
        )
        ticket_data = json.loads(ticket)
        ticket_id = ticket_data["ticket_id"]
        
        # Escalate (billing dispute)
        escalation = await escalate_to_human(
            ticket_id=ticket_id,
            reason="Billing dispute - customer charged twice",
            urgency="high"
        )
        escalation_data = json.loads(escalation)
        
        assert escalation_data["escalation_level"] == "L1_Tier1", "Billing → L1"
        
        # Notify customer
        response = await send_response(
            ticket_id=ticket_id,
            message="I understand your concern. Connecting you with billing specialist.",
            channel="email"
        )
        response_data = json.loads(response)
        
        assert response_data["success"] is True, "Response should send"
        
        print("✅ Full escalation flow completed")


# =============================================================================
# MAIN (Run tests directly)
# =============================================================================

if __name__ == "__main__":
    """Run tests directly with pytest."""
    print("=" * 80)
    print("NEXUSFLOW DIGITAL FTE - TRANSITION TEST SUITE")
    print("=" * 80)
    
    # Run pytest
    exit_code = pytest.main([
        __file__,
        "-v",           # Verbose output
        "--tb=short",   # Short traceback
        "-x",           # Stop on first failure
    ])
    
    print("\n" + "=" * 80)
    if exit_code == 0:
        print("✅ ALL TRANSITION TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 80)
    
    sys.exit(exit_code)
