"""Test OpenAI Agents SDK usage"""
from dotenv import load_dotenv
load_dotenv()
import os
from agents import Agent, Runner

# Create an agent
agent = Agent(
    name="Customer Support Agent",
    instructions="You are a helpful customer support assistant for NexusFlow project management software."
)

# Run the agent
async def test():
    result = await Runner.run(agent, "Hello, how do I export Gantt charts?")
    print("Response:", result.final_output)
    print("Tools used:", [call.tool_name for call in result.tool_calls] if result.tool_calls else [])

if __name__ == "__main__":
    import asyncio
    asyncio.run(test())
