"""
before_agent_callback — root_agent

PURPOSE:
    Fires at session start (and on every re-entry to root_agent after a sub-agent
    transfer — the early-return guard prevents re-processing on re-entry).

    1. Reads 'telephony-caller-id' from session params (CES system variable for telephony).
    2. If present, calls recognize_customer(phone_number=<value>) to look up the caller.
    3. If absent, or if recognize_customer returns no match, sets the default demo persona.
    4. Writes 'customer_profile' (JSON string) and 'active_language' = 'English' to state.
    5. Returns a deterministic LlmResponse greeting — bypassing the LLM entirely for
       the first turn, guaranteeing consistent demo experience.

PLATFORM GLOBALS (do NOT import):
    CallbackContext, Content, Part, LlmResponse are auto-provided at runtime.
"""

import json
from typing import Optional


def before_agent_callback(callback_context: CallbackContext) -> Optional[Content]:
    state = callback_context.state

    # -------------------------------------------------------------------------
    # EARLY RETURN: customer_profile already set means we've already done the
    # recognition. This happens when root_agent is re-entered after a sub-agent
    # completes its task. Don't reset state or re-greet.
    # -------------------------------------------------------------------------
    if state.get("customer_profile"):
        return None

    # -------------------------------------------------------------------------
    # READ TELEPHONY CALLER ID: CES injects 'telephony-caller-id' into session
    # params for telephony channel calls. In the simulator it is absent.
    # -------------------------------------------------------------------------
    phone_number = state.get("telephony-caller-id", "")

    customer_profile = None

    if phone_number:
        try:
            result = tools.recognize_customer(phone_number=phone_number)
            if result and result.get("customer_id"):
                customer_profile = {
                    "customer_id": result["customer_id"],
                    "first_name": result.get("first_name", ""),
                    "last_name": result.get("last_name", ""),
                    "account_status": result.get("account_status", "Active"),
                    "is_default_persona": False,
                }
        except Exception:
            # Recognition failed — fall through to default persona
            customer_profile = None

    # -------------------------------------------------------------------------
    # DEFAULT PERSONA: Used when no ANI is present (simulator) or when
    # recognize_customer finds no match for the number.
    # -------------------------------------------------------------------------
    if customer_profile is None:
        customer_profile = {
            "customer_id": "DEMO-001",
            "first_name": "there",
            "last_name": "",
            "account_status": "Active",
            "is_default_persona": True,
        }

    # Write variables to session state
    state["customer_profile"] = json.dumps(customer_profile)
    state["active_language"] = "English"

    # -------------------------------------------------------------------------
    # DETERMINISTIC GREETING: Return Content to bypass LLM for first turn.
    # before_agent_callback returns Optional[Content], NOT LlmResponse.
    # -------------------------------------------------------------------------
    if not customer_profile["is_default_persona"]:
        first_name = customer_profile["first_name"]
        last_name = customer_profile["last_name"]
        greeting = (
            f"Hi! Thanks for calling Vodafone Ziggo support. "
            f"I've automatically recognised your number. "
            f"Am I speaking with {first_name} {last_name}?"
        )
    else:
        greeting = (
            "Hi! Thanks for calling Vodafone Ziggo support. "
            "How can I help you today?"
        )

    return Content(role="model", parts=[Part(text=greeting)])
