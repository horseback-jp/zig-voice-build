"""
before_model_callback — root_agent

PURPOSE:
    1. ESCALATION TRIGGER PATTERN: Reads '_escalation_trigger' from state.
       If set to 'escalate', assembles context_summary from session variables,
       calls escalate_to_human deterministically, clears the trigger, and
       returns a deterministic transfer response.

    2. SILENCE HANDLING (root_agent only): Detects 'NO_USER_ACTIVITY' / silence
       events. Increments '_silence_count'. After 3 consecutive silences, plays
       farewell and ends session.

PLATFORM GLOBALS (do NOT import):
    CallbackContext, LlmRequest, LlmResponse, Part are auto-provided at runtime.
"""

import json
import re
from typing import Optional


def _is_user_inactive(contents: list) -> bool:
    """Check if the latest user message is a silence / no-activity signal."""
    if len(contents) < 2:
        return False
    last_content = contents[-1]
    for part in last_content.parts:
        text = part.text or ""
        if re.search(
            r"(no user activity detected|NO_USER_ACTIVITY)",
            text,
            re.IGNORECASE,
        ):
            return True
    return False


def _get_last_agent_text(contents: list) -> str:
    """Return the most recent agent text from conversation history."""
    for content in reversed(contents):
        if content.role == "model":
            for part in content.parts:
                if part.text:
                    return part.text
    return "How can I help you today?"


def before_model_callback(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
    state = callback_context.state

    # -------------------------------------------------------------------------
    # SILENCE HANDLING
    # -------------------------------------------------------------------------
    try:
        if _is_user_inactive(llm_request.contents):
            silence_count = int(state.get("_silence_count") or 0) + 1
            state["_silence_count"] = str(silence_count)

            if silence_count < 3:
                last_text = _get_last_agent_text(llm_request.contents)
                if silence_count == 1:
                    msg = f"Sorry, I didn't quite catch that. {last_text}"
                else:
                    msg = f"I still can't hear you. {last_text}"
                return LlmResponse.from_parts(parts=[Part.from_text(text=msg)])
            else:
                return LlmResponse.from_parts(parts=[
                    Part.from_text(
                        text=(
                            "I'm sorry, I'm unable to hear you. "
                            "Please try calling us again. Have a wonderful day!"
                        )
                    ),
                    Part.from_function_call(
                        name="end_session",
                        args={"session_escalated": False, "reason": "silence_limit_reached"},
                    ),
                ])
        else:
            # User spoke — reset silence counter
            state["_silence_count"] = "0"
    except Exception:
        pass

    # -------------------------------------------------------------------------
    # ESCALATION TRIGGER PATTERN
    # -------------------------------------------------------------------------
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
        "Escalation requested from root_agent. No spoke agent was active."
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
                "Of course. Let me connect you with one of our advisors right away. "
                "Please hold for just a moment."
            )
        ),
        Part.from_function_call(
            name="end_session",
            args={"session_escalated": True, "reason": "escalation_trigger"},
        ),
    ])
