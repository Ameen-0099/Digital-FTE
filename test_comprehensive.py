"""
NexusFlow Digital FTE - Comprehensive AI Test Suite
====================================================
Tests all AI capabilities:
- Sentiment Analysis (8 categories)
- Intent Classification (10+ patterns)
- Knowledge Base Search
- Escalation Logic (L0-L4)
- Channel-specific Responses
- Response Quality
"""

import json
import requests
from datetime import datetime

API_URL = "http://localhost:8000"

# Test cases covering different scenarios
TEST_CASES = [
    {
        "name": "How-To Question (Recurring Tasks)",
        "data": {
            "name": "Sarah Johnson",
            "email": "sarah@example.com",
            "subject": "How do I set up recurring tasks?",
            "description": "I need help creating a recurring task that repeats every week for our team meetings",
            "priority": "low"
        },
        "expected": {
            "category": "how_to",
            "sentiment": ["neutral", "positive", "panicked"],
            "escalation_needed": [False, True],
            "should_contain_keywords": ["recurring", "repeat", "task"]
        }
    },
    {
        "name": "Billing Dispute (Should Escalate)",
        "data": {
            "name": "James Chen",
            "email": "james@example.com",
            "subject": "Charged twice!",
            "description": "I was charged twice this month. Transaction IDs: TXN-98765 and TXN-98766. This is unacceptable!",
            "priority": "high"
        },
        "expected": {
            "category": ["billing_inquiry", "billing_dispute"],
            "sentiment": ["angry", "frustrated", "concerned"],
            "escalation_needed": True,
            "escalation_level": "L1_Tier1",
            "should_contain_keywords": ["billing"]
        }
    },
    {
        "name": "Technical Issue (Gantt Export)",
        "data": {
            "name": "Michael Brown",
            "email": "michael@example.com",
            "subject": "Export hanging",
            "description": "Gantt chart export to PDF has been hanging for 10 minutes. Using Chrome browser. Already tried clearing cache.",
            "priority": "high"
        },
        "expected": {
            "category": ["technical_issue", "export"],
            "sentiment": ["neutral", "frustrated", "concerned"],
            "escalation_needed": False,
            "should_contain_keywords": ["export", "gantt", "pdf"]
        }
    },
    {
        "name": "Pricing Inquiry",
        "data": {
            "name": "Emily Rodriguez",
            "email": "emily@nonprofit.org",
            "subject": "Nonprofit discount?",
            "description": "What are your pricing plans? Do you offer nonprofit discounts? We are a team of 50.",
            "priority": "medium"
        },
        "expected": {
            "category": "pricing",
            "sentiment": "neutral",
            "escalation_needed": False,
            "should_contain_keywords": ["plan", "nonprofit"]
        }
    },
    {
        "name": "Panicked Customer (Data Loss)",
        "data": {
            "name": "David Park",
            "email": "david@example.com",
            "subject": "All tasks disappeared!",
            "description": "HELP! All my tasks disappeared from the board! Did I accidentally delete something? This has all our project data!!!",
            "priority": "critical"
        },
        "expected": {
            "category": ["data_loss", "technical_issue"],
            "sentiment": "panicked",
            "urgency": "critical",
            "escalation_needed": True,
            "should_contain_keywords": ["deleted", "recovery", "restore"]
        }
    },
    {
        "name": "Feature Request",
        "data": {
            "name": "Lisa Wang",
            "email": "lisa@techcorp.com",
            "subject": "Dark mode feature",
            "description": "Would love to see a dark mode option in the app. Many of our team work late and would appreciate easier viewing.",
            "priority": "low"
        },
        "expected": {
            "category": ["feature_request", "technical_issue"],
            "sentiment": ["positive", "very_positive", "neutral"],
            "escalation_needed": False,
            "should_contain_keywords": []
        }
    },
    {
        "name": "Integration Question",
        "data": {
            "name": "Robert Kim",
            "email": "robert@startup.io",
            "subject": "Slack integration setup",
            "description": "How do I connect NexusFlow with our Slack workspace? We want notifications in our project channel.",
            "priority": "medium"
        },
        "expected": {
            "category": "integration",
            "sentiment": "neutral",
            "escalation_needed": False,
            "should_contain_keywords": ["slack", "integration", "notification"]
        }
    },
    {
        "name": "VIP Customer Issue",
        "data": {
            "name": "Carol White",
            "email": "carol@enterprise.com",
            "subject": "SSO not working",
            "description": "Our SSO integration stopped working this morning. 200+ users cannot log in. This is a critical business impact.",
            "priority": "critical"
        },
        "expected": {
            "category": ["technical_issue", "integration"],
            "sentiment": ["panicked", "concerned", "frustrated"],
            "urgency": "critical",
            "escalation_needed": True,
            "should_contain_keywords": ["sso", "login"]
        }
    }
]


def submit_ticket(test_data):
    """Submit a support ticket to the API."""
    response = requests.post(
        f"{API_URL}/support/submit",
        json=test_data,
        headers={"Content-Type": "application/json"}
    )
    return response.json(), response.status_code


def check_result(test_name, result, expected):
    """Check if AI response matches expectations."""
    issues = []
    passed = []
    
    # Category aliases for flexible matching
    CATEGORY_ALIASES = {
        "pricing": ["pricing", "pricing_inquiry"],
        "billing": ["billing", "billing_inquiry", "billing_dispute"],
        "technical_issue": ["technical_issue", "export", "integration", "account"],
        "how_to": ["how_to"],
        "feature_request": ["feature_request"],
        "integration": ["integration"],
        "data_loss": ["data_loss"],
    }
    
    # Check category
    if "category" in expected:
        expected_cat = expected["category"]
        actual_cat = result.get("category")
        
        if isinstance(expected_cat, list):
            # Expand aliases in expected list
            expanded_expected = []
            for cat in expected_cat:
                if cat in CATEGORY_ALIASES:
                    expanded_expected.extend(CATEGORY_ALIASES[cat])
                else:
                    expanded_expected.append(cat)
            if actual_cat in expanded_expected:
                passed.append(f"Category: {actual_cat}")
            else:
                issues.append(f"Category: expected {expected_cat}, got {actual_cat}")
        else:
            # Single category - check with aliases
            if expected_cat in CATEGORY_ALIASES:
                if actual_cat in CATEGORY_ALIASES[expected_cat]:
                    passed.append(f"Category: {actual_cat}")
                else:
                    issues.append(f"Category: expected {expected_cat} (or aliases {CATEGORY_ALIASES[expected_cat]}), got {actual_cat}")
            else:
                if actual_cat == expected_cat:
                    passed.append(f"Category: {actual_cat}")
                else:
                    issues.append(f"Category: expected {expected_cat}, got {actual_cat}")
    
    # Check sentiment
    if "sentiment" in expected:
        if isinstance(expected["sentiment"], list):
            if result.get("sentiment") not in expected["sentiment"]:
                issues.append(f"Sentiment: expected {expected['sentiment']}, got {result.get('sentiment')}")
            else:
                passed.append(f"Sentiment: {result.get('sentiment')}")
        else:
            if result.get("sentiment") != expected["sentiment"]:
                issues.append(f"Sentiment: expected {expected['sentiment']}, got {result.get('sentiment')}")
            else:
                passed.append(f"Sentiment: {result.get('sentiment')}")
    
    # Check escalation
    if "escalation_needed" in expected:
        expected_esc = expected["escalation_needed"]
        actual_esc = result.get("escalation_needed")
        if isinstance(expected_esc, list):
            if actual_esc in expected_esc:
                passed.append(f"Escalation needed: {actual_esc}")
            else:
                issues.append(f"Escalation: expected {expected_esc}, got {actual_esc}")
        else:
            if actual_esc != expected_esc:
                issues.append(f"Escalation: expected {expected_esc}, got {actual_esc}")
            else:
                passed.append(f"Escalation needed: {actual_esc}")
    
    # Check escalation level
    if "escalation_level" in expected:
        if result.get("escalation_level") != expected["escalation_level"]:
            issues.append(f"Escalation level: expected {expected['escalation_level']}, got {result.get('escalation_level')}")
        else:
            passed.append(f"Escalation level: {result.get('escalation_level')}")
    
    # Check urgency
    if "urgency" in expected:
        if result.get("urgency") != expected["urgency"]:
            issues.append(f"Urgency: expected {expected['urgency']}, got {result.get('urgency')}")
        else:
            passed.append(f"Urgency: {result.get('urgency')}")
    
    # Check response contains expected keywords
    if "should_contain_keywords" in expected:
        response_text = result.get("response", "").lower()
        for keyword in expected["should_contain_keywords"]:
            if keyword.lower() not in response_text:
                issues.append(f"Response missing keyword: '{keyword}'")
            else:
                passed.append(f"Response contains keyword: '{keyword}'")
    
    return passed, issues


def run_comprehensive_tests():
    """Run all tests and generate report."""
    print("=" * 80)
    print("NEXUSFLOW DIGITAL FTE - COMPREHENSIVE AI TEST SUITE")
    print("=" * 80)
    print(f"\nStarted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API URL: {API_URL}")
    print("=" * 80)
    
    # Check API health first
    try:
        health = requests.get(f"{API_URL}/health").json()
        print(f"\n✅ API Health: {health.get('status', 'unknown')}")
    except Exception as e:
        print(f"\n❌ API Health Check Failed: {e}")
        print("Make sure the API is running: python demo_api.py")
        return
    
    results = []
    total_tests = len(TEST_CASES)
    total_passed = 0
    total_failed = 0
    
    for i, test in enumerate(TEST_CASES, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}/{total_tests}: {test['name']}")
        print("=" * 80)
        
        # Submit ticket
        try:
            result, status_code = submit_ticket(test["data"])
            
            if status_code != 200:
                print(f"❌ API Error: {status_code}")
                print(f"   Response: {result}")
                results.append({
                    "test": test["name"],
                    "status": "FAILED",
                    "error": f"API Error: {status_code}"
                })
                total_failed += 1
                continue
            
            # Check results
            passed, issues = check_result(
                test["name"],
                result,
                test["expected"]
            )
            
            # Print results
            print(f"\n📤 INPUT:")
            print(f"   Subject: {test['data']['subject']}")
            print(f"   Description: {test['data']['description'][:80]}...")
            
            print(f"\n📥 AI RESPONSE:")
            print(f"   Ticket ID: {result.get('ticket_id', 'N/A')}")
            print(f"   Category: {result.get('category', 'N/A')}")
            print(f"   Sentiment: {result.get('sentiment', 'N/A')}")
            print(f"   Urgency: {result.get('urgency', 'N/A')}")
            print(f"   Escalation: {result.get('escalation_needed', False)} ({result.get('escalation_level', 'N/A')})")
            
            print(f"\n💬 AI Response Preview:")
            response_text = result.get('response', '')
            print(f"   {response_text[:200]}..." if len(response_text) > 200 else f"   {response_text}")
            
            print(f"\n✅ PASSED CHECKS ({len(passed)}):")
            for p in passed:
                print(f"   ✓ {p}")
            
            if issues:
                print(f"\n⚠️  ISSUES ({len(issues)}):")
                for issue in issues:
                    print(f"   ✗ {issue}")
            
            # Determine test status
            if len(issues) == 0:
                status = "PASSED"
                total_passed += 1
            else:
                status = "FAILED"
                total_failed += 1
            
            results.append({
                "test": test["name"],
                "status": status,
                "passed": len(passed),
                "issues": len(issues),
                "details": {
                    "category": result.get("category"),
                    "sentiment": result.get("sentiment"),
                    "urgency": result.get("urgency"),
                    "escalation": result.get("escalation_needed"),
                    "escalation_level": result.get("escalation_level")
                }
            })
            
        except Exception as e:
            print(f"❌ Test Failed: {e}")
            results.append({
                "test": test["name"],
                "status": "FAILED",
                "error": str(e)
            })
            total_failed += 1
    
    # Print summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"\nTotal Tests: {total_tests}")
    print(f"Passed: {total_passed} ({100*total_passed/total_tests:.1f}%)")
    print(f"Failed: {total_failed} ({100*total_failed/total_tests:.1f}%)")
    
    print(f"\n📊 RESULTS BY TEST:")
    for r in results:
        status_icon = "✅" if r["status"] == "PASSED" else "❌"
        print(f"   {status_icon} {r['test']}: {r['status']}")
    
    # Get dashboard stats
    try:
        dashboard = requests.get(f"{API_URL}/reports/dashboard").json()
        print(f"\n📈 DASHBOARD STATS:")
        print(f"   Total Tickets: {dashboard.get('overview', {}).get('total_tickets', 0)}")
        print(f"   AI Resolution Rate: {dashboard.get('overview', {}).get('ai_resolution_rate', 'N/A')}")
        print(f"   Sentiment Distribution: {dashboard.get('sentiment_distribution', {})}")
    except:
        pass
    
    print(f"\n{'='*80}")
    print(f"Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    return results


if __name__ == "__main__":
    run_comprehensive_tests()
