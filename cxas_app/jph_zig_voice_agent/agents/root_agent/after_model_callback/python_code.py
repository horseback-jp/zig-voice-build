"""
after_model_callback — root_agent

PURPOSE:
    Injects a deterministic locale-aware farewell message before end_session
    when the LLM ends the session without speaking first.

    - If active_language == 'Dutch': injects Dutch farewell.
    - Otherwise: injects English farewell.

    Uses callback_context.events to detect prior agent text in the same turn
    (multi-model-call guard) to prevent double-injection.

PLATFORM GLOBALS (do NOT import):
    CallbackContext, LlmResponse, Part are auto-provided at runtime.
"""

from typing import Optional


def after_model_callback(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> Optional[LlmResponse]:

    # -------------------------------------------------------------------------
    # STEP 1: Does this model call contain end_session?
    # -------------------------------------------------------------------------
    has_end_session = False
    has_text_this_call = False

    for part in llm_response.content.parts:
        if part.has_function_call("end_session"):
            has_end_session = True
        else:
            content = part.text_or_transcript()
            if content and len(content.strip()) > 0:
                has_text_this_call = True

    # No end_session, or LLM already said something in this call — no-op.
    if not has_end_session or has_text_this_call:
        return None

    # -------------------------------------------------------------------------
    # STEP 2: Check if the agent already produced text in an EARLIER model call
    # within this same turn (multi-model-call guard).
    # -------------------------------------------------------------------------
    for event in reversed(callback_context.events):
        if event.is_user():
            break
        if event.is_agent():
            for p in event.parts():
                content = p.text_or_transcript()
                if content and len(content.strip()) > 0:
                    return None

    # -------------------------------------------------------------------------
    # STEP 3: Inject locale-aware farewell BEFORE end_session.
    # -------------------------------------------------------------------------
    active_language = callback_context.state.get("active_language", "English")

    if active_language == "Dutch":
        farewell = "Bedankt voor uw gesprek met Vodafone Ziggo. Fijne dag nog!"
    else:
        farewell = "Thank you for calling Vodafone Ziggo. Have a wonderful day!"

    new_parts = [Part.from_text(text=farewell)]
    new_parts.extend(llm_response.content.parts)
    return LlmResponse.from_parts(parts=new_parts)
