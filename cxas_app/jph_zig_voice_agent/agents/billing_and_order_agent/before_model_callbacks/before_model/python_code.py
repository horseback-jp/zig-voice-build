"""
before_model_callback — billing_and_order_agent

PURPOSE:
    Implements the ESCALATION TRIGGER PATTERN for this spoke agent.
    Reads '_escalation_trigger' from state. If set to 'escalate', assembles
    context_summary from session variables, calls escalate_to_human
    deterministically, clears the trigger, and returns a deterministic response.

    WHY on ALL agents:
    Sub-agent flows bypass root_agent callbacks. If this callback existed only
    on root_agent, escalation triggers set while billing_and_order_agent is
    active would never be intercepted.

PLATFORM GLOBALS (do NOT import):
    CallbackContext, LlmRequest, LlmResponse, Part are auto-provided at runtime.
"""

import json
from typing import Optional


def before_model_callback(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
    state = callback_context.state

    escalation_trigger = state.get("_escalation_trigger", "")
    if escalation_trigger != "escalate":
        return None

    # Clear trigger immediately to prevent re-firing
    state["_escalation_trigger"] = ""

    # Build context_summary from session state
    customer_profile_raw = state.get("customer_profile", "{}")
    try:
        profile = json.loads(customer_profile_raw)
    except Exception:
        profile = {}

    customer_id = profile.get("customer_id", "UNKNOWN")
    first_name = profile.get("first_name", "")
    last_name = profile.get("last_name", "")
    active_language = state.get("active_language", "English")

    context_summary = (
        f"Customer: {first_name} {last_name} (ID: {customer_id}). "
        f"Active language: {active_language}. "
        "Escalation triggered from billing_and_order_agent. "
        "Customer was being assisted with billing or order queries."
    )

    try:
        tools.escalate_to_human(
            customer_id=customer_id,
            context_summary=context_summary,
        )
    except Exception:
        pass

    return LlmResponse.from_parts(parts=[
        Part.from_text(
            text=(
                "Of course. Let me connect you with one of our billing advisors now. "
                "Please hold for just a moment."
            )
        ),
        Part.from_function_call(
            name="end_session",
            args={"session_escalated": True, "reason": "escalation_trigger"},
        ),
    ])
