"""
NexusFlow Customer Success Digital FTE - Production Agent
==========================================================

This package contains production-ready agent components for the
NexusFlow Customer Success Digital FTE.

Modules:
- tools: OpenAI Agents SDK @function_tool decorated functions
- prompts: Production-grade system prompts
"""

from .tools import (
    search_knowledge_base,
    create_ticket,
    get_customer_history,
    escalate_to_human,
    send_response,
    get_all_tool_names,
    get_tool_description
)

from .prompts import (
    CUSTOMER_SUCCESS_SYSTEM_PROMPT,
    PROMPT_METADATA,
    validate_prompt
)

__all__ = [
    # Tools
    "search_knowledge_base",
    "create_ticket",
    "get_customer_history",
    "escalate_to_human",
    "send_response",
    "get_all_tool_names",
    "get_tool_description",
    # Prompts
    "CUSTOMER_SUCCESS_SYSTEM_PROMPT",
    "PROMPT_METADATA",
    "validate_prompt"
]
