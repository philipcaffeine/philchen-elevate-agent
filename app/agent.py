"""Core ADK LlmAgent Construction & Query Execution."""
import asyncio
import os
import sys
from typing import Dict, Any, Tuple, List, Optional

from google.adk.agents import LlmAgent

from . import config
from .prompt import POLICY_AGENT_PROMPT
from .guardrails import (
    redact_spii,
    check_prompt_injection,
    check_domain_containment,
    validate_caller,
)
from .tools import (
    search_policy_docs,
    list_concepts,
    read_concept,
    get_employee_profile,
    get_leave_balances,
    submit_leave_request,
    update_contact_info,
    get_incident_ticket,
    create_incident_ticket,
    add_ticket_comment,
    update_ticket_status,
    execute_medical_leave_workflow,
)


def _build_model():
    """Build model reference for ADK. Handles Vertex AI or API key if provided."""
    if os.getenv("GEMINI_API_KEY"):
        return config.GEMINI_MODEL

    try:
        from google.adk.models.google_llm import Gemini
        from google.genai import Client
        import subprocess

        class FreshGemini(Gemini):
            @property
            def api_client(self) -> Client:
                client_kwargs = {
                    "vertexai": True,
                    "project": config.GOOGLE_CLOUD_PROJECT,
                    "location": config.GOOGLE_CLOUD_LOCATION,
                }
                # Attempt to pass gcloud access token if available
                try:
                    token = subprocess.check_output(
                        ["gcloud", "auth", "print-access-token"],
                        stderr=subprocess.DEVNULL,
                    ).decode().strip()
                    if token:
                        from google.oauth2 import credentials
                        client_kwargs["credentials"] = credentials.Credentials(token)
                except Exception:
                    pass
                return Client(**client_kwargs)

        return FreshGemini(model=config.GEMINI_MODEL)
    except Exception:
        # Default string fallback
        return config.GEMINI_MODEL


# Tool Registry for the HR Agent
AGENT_TOOLS = [
    search_policy_docs,
    list_concepts,
    read_concept,
    get_employee_profile,
    get_leave_balances,
    submit_leave_request,
    update_contact_info,
    get_incident_ticket,
    create_incident_ticket,
    add_ticket_comment,
    update_ticket_status,
    execute_medical_leave_workflow,
]

# Root Agent Instance
root_agent = LlmAgent(
    name="hr_policy_agent",
    description="Altostrat Singapore Enterprise HR Agentic Virtual Assistant",
    model=_build_model(),
    instruction=POLICY_AGENT_PROMPT,
    tools=AGENT_TOOLS,
)

_session_service = None


def _ensure_runner():
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService

    global _session_service
    if _session_service is None:
        _session_service = InMemorySessionService()
    return Runner(app_name=config.APP_NAME, agent=root_agent, session_service=_session_service)


async def _ensure_session_async(user_id: str, session_id: str):
    try:
        await _session_service.create_session(
            app_name=config.APP_NAME, user_id=user_id, session_id=session_id
        )
    except Exception:
        pass


async def run_agent_turn(
    message: str,
    caller_id: str = "EMP1024",
    session_id: str = "session-1",
) -> Dict[str, Any]:
    """Execute an agent turn with input guardrails, ADK execution, and output redaction."""
    # 1. Pre-execution Safety Guardrails
    is_safe, injection_msg = check_prompt_injection(message)
    if not is_safe:
        return {
            "answer": injection_msg,
            "blocked": True,
            "reason": "prompt_injection",
            "evidence": [],
        }

    is_contained, domain_msg = check_domain_containment(message)
    if not is_contained:
        return {
            "answer": domain_msg,
            "blocked": True,
            "reason": "domain_containment",
            "evidence": [],
        }

    # Redact input for logging/safety
    safe_input = redact_spii(message)

    # 2. ADK Runner Execution
    try:
        from google.genai import types
        runner = _ensure_runner()
        await _ensure_session_async(caller_id, session_id)
        msg_content = types.Content(role="user", parts=[types.Part(text=safe_input)])

        final_text = ""
        evidence = []
        async for event in runner.run_async(
            user_id=caller_id, session_id=session_id, new_message=msg_content
        ):
            if not (event.content and event.content.parts):
                continue
            for part in event.content.parts:
                fr = getattr(part, "function_response", None)
                if fr is not None:
                    evidence.append({
                        "tool": getattr(fr, "name", "unknown_tool"),
                        "payload": getattr(fr, "response", {}),
                    })
            if event.is_final_response() and event.content.parts:
                texts = [p.text for p in event.content.parts if getattr(p, "text", None)]
                if texts:
                    final_text = "\n".join(texts)

        # 3. Post-execution Output Masking
        sanitized_output = redact_spii(final_text)
        return {
            "answer": sanitized_output,
            "blocked": False,
            "evidence": evidence,
        }
    except Exception as e:
        # Fallback graceful response when LLM credentials or offline network is tripped
        return {
            "answer": f"I am temporarily unable to connect to the agent service. Please try again in a moment. (Error: {str(e)[:80]})",
            "blocked": False,
            "error": str(e),
            "evidence": [],
        }
