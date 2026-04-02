"""
NexusFlow Customer Success Digital FTE - Pytest Configuration
==============================================================

Shared fixtures and configuration for all test suites.
"""

import pytest
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# PYTEST CONFIGURATION
# =============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow running"
    )


# =============================================================================
# SHARED FIXTURES
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_customer_data():
    """Test customer data for use across tests."""
    return {
        "existing": {
            "email": "alice@techcorp.com",
            "name": "Alice Johnson",
            "company": "TechCorp Inc.",
            "plan": "Professional"
        },
        "vip": {
            "email": "carol@enterprise.com",
            "name": "Carol White",
            "company": "Enterprise Corp",
            "plan": "Business"
        },
        "new": {
            "email": "newcustomer@example.com",
            "name": "New Customer",
            "company": "Unknown",
            "plan": "Unknown"
        }
    }


@pytest.fixture
def test_knowledge_queries():
    """Test knowledge base queries for use across tests."""
    return {
        "export": "how to export gantt chart to pdf",
        "recurring": "set up recurring tasks",
        "billing": "duplicate charge refund",
        "sso": "SSO SAML configuration",
        "integration": "slack integration setup"
    }


@pytest.fixture
def test_channels():
    """Test channel configurations."""
    return {
        "email": {
            "name": "email",
            "max_length": None,
            "tone": "formal",
            "emoji": False
        },
        "whatsapp": {
            "name": "whatsapp",
            "max_length": 300,
            "tone": "casual",
            "emoji": True
        },
        "web_form": {
            "name": "web_form",
            "max_length": 1000,
            "tone": "professional",
            "emoji": "optional"
        }
    }


@pytest.fixture
def test_escalation_scenarios():
    """Test escalation scenarios."""
    return {
        "human_request": {
            "reason": "Customer explicitly requested human agent",
            "expected_level": "L1_Tier1"
        },
        "billing_dispute": {
            "reason": "Billing dispute requires verification - duplicate charge",
            "expected_level": "L1_Tier1"
        },
        "legal": {
            "reason": "Legal matter - customer mentioned lawsuit",
            "expected_level": "L4_Management"
        },
        "security": {
            "reason": "Security breach - unauthorized access detected",
            "expected_level": "L3_Tier3"
        },
        "technical": {
            "reason": "Advanced API integration issue requires specialist",
            "expected_level": "L2_Tier2"
        }
    }
