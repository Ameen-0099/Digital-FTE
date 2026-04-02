"""Test script to check OpenAI initialization"""
from dotenv import load_dotenv
load_dotenv()
import os
import sys

sys.path.insert(0, 'production')

print("1. Loading environment...")
print(f"   OPENAI_API_KEY: {os.getenv('OPENAI_API_KEY', 'NOT SET')[:20]}...")
print(f"   OPENAI_MODEL: {os.getenv('OPENAI_MODEL', 'NOT SET')}")

print("\n2. Importing OpenAI Agents SDK...")
try:
    from agents import Runner, Agent
    print("   ✅ Runner and Agent imported")
except Exception as e:
    print(f"   ❌ Import failed: {e}")
    sys.exit(1)

print("\n3. Importing production tools...")
try:
    from production.agent.tools import (
        search_knowledge_base,
        create_ticket,
        get_customer_history,
        escalate_to_human,
        send_response,
    )
    print("   ✅ Tools imported")
except Exception as e:
    print(f"   ❌ Tools import failed: {e}")

print("\n4. Importing prompts...")
try:
    from production.agent.prompts import CUSTOMER_SUCCESS_SYSTEM_PROMPT
    print(f"   ✅ Prompt imported ({len(CUSTOMER_SUCCESS_SYSTEM_PROMPT)} chars)")
except Exception as e:
    print(f"   ❌ Prompt import failed: {e}")
    sys.exit(1)

print("\n5. Creating Agent...")
try:
    agent = Agent(
        name="NexusFlow Customer Success Digital FTE",
        instructions=CUSTOMER_SUCCESS_SYSTEM_PROMPT,
        tools=[
            search_knowledge_base,
            create_ticket,
            get_customer_history,
            escalate_to_human,
            send_response,
        ],
    )
    print("   ✅ Agent created")
except Exception as e:
    print(f"   ❌ Agent creation failed: {e}")
    sys.exit(1)

print("\n6. Testing Runner...")
import asyncio
async def test():
    try:
        result = await Runner.run(agent, "Hello, how do I export Gantt charts?")
        print(f"   ✅ Response received ({len(result.final_output)} chars)")
        print(f"   Response preview: {result.final_output[:100]}...")
        return True
    except Exception as e:
        print(f"   ❌ Runner failed: {e}")
        return False

success = asyncio.run(test())
print(f"\n{'='*60}")
print(f"OpenAI Integration: {'✅ WORKING' if success else '❌ FAILED'}")
print(f"{'='*60}")
