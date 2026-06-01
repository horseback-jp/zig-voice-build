"""
Callback tests — root_agent / before_model_callback

Tests cover:
  - No-op path: no escalation trigger, no silence event
  - Escalation trigger fires: escalate_to_human called, LlmResponse returned
  - Silence handling: first silence (reprompt), second silence (reprompt), third (farewell + end_session)
  - Silence counter reset when user speaks
"""

import sys
import os
import json
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "..", "agents", "root_agent",
    "before_model_callbacks", "before_model",
))

import python_code  # noqa: E402
python_code.tools = MagicMock()
python_code.LlmResponse = MagicMock()
python_code.Part = MagicMock()

from python_code import before_model_callback  # noqa: E402
from cxas_scrapi.utils.callback_libs import CallbackContext  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user_content(text: str):
    """Minimal content object mimicking a user turn."""
    part = MagicMock()
    part.text = text
    content = MagicMock()
    content.role = "user"
    content.parts = [part]
    return content


def _make_model_content(text: str):
    """Minimal content object mimicking an agent turn."""
    part = MagicMock()
    part.text = text
    content = MagicMock()
    content.role = "model"
    content.parts = [part]
    return content


def _make_request(*contents):
    req = MagicMock()
    req.contents = list(contents)
    return req


def _silence_content():
    return _make_user_content("NO_USER_ACTIVITY")


# ---------------------------------------------------------------------------
# TestNoOpPath
# ---------------------------------------------------------------------------
class TestNoOpPath:
    """No escalation trigger and no silence → callback must return None."""

    def setup_method(self):
        python_code.tools.reset_mock()
        python_code.LlmResponse.reset_mock()

    def test_returns_none_with_empty_trigger_and_normal_speech(self):
        ctx = CallbackContext(state={"_escalation_trigger": ""})
        req = _make_request(
            _make_model_content("How can I help?"),
            _make_user_content("I have a question about my bill."),
        )
        result = before_model_callback(ctx, req)
        assert result is None

    def test_returns_none_with_absent_trigger_key(self):
        ctx = CallbackContext(state={})
        req = _make_request(
            _make_model_content("How can I help?"),
            _make_user_content("Hello"),
        )
        result = before_model_callback(ctx, req)
        assert result is None

    def test_escalate_to_human_not_called_on_no_op(self):
        ctx = CallbackContext(state={})
        req = _make_request(
            _make_model_content("How can I help?"),
            _make_user_content("Hello"),
        )
        before_model_callback(ctx, req)
        python_code.tools.escalate_to_human.assert_not_called()


# ---------------------------------------------------------------------------
# TestEscalationTrigger
# ---------------------------------------------------------------------------
class TestEscalationTrigger:
    """_escalation_trigger == 'escalate' → escalate_to_human called, LlmResponse returned."""

    def setup_method(self):
        python_code.tools.reset_mock()
        python_code.LlmResponse.reset_mock()
        python_code.Part.reset_mock()

    def test_escalate_to_human_called_with_customer_id(self):
        profile = json.dumps({
            "customer_id": "CUST-123",
            "first_name": "Jan",
            "last_name": "de Vries",
        })
        ctx = CallbackContext(state={
            "_escalation_trigger": "escalate",
            "customer_profile": profile,
            "active_language": "English",
        })
        req = _make_request(_make_user_content("transfer me please"))
        before_model_callback(ctx, req)
        python_code.tools.escalate_to_human.assert_called_once()
        call_kwargs = python_code.tools.escalate_to_human.call_args[1]
        assert call_kwargs["customer_id"] == "CUST-123"

    def test_trigger_cleared_after_escalation(self):
        profile = json.dumps({"customer_id": "CUST-123", "first_name": "Jan", "last_name": "de Vries"})
        ctx = CallbackContext(state={
            "_escalation_trigger": "escalate",
            "customer_profile": profile,
            "active_language": "English",
        })
        req = _make_request(_make_user_content("escalate"))
        before_model_callback(ctx, req)
        assert ctx.state["_escalation_trigger"] == ""

    def test_llm_response_returned_on_escalation(self):
        profile = json.dumps({"customer_id": "CUST-123", "first_name": "Jan", "last_name": "de Vries"})
        ctx = CallbackContext(state={
            "_escalation_trigger": "escalate",
            "customer_profile": profile,
            "active_language": "English",
        })
        req = _make_request(_make_user_content("escalate"))
        result = before_model_callback(ctx, req)
        python_code.LlmResponse.from_parts.assert_called_once()
        assert result is python_code.LlmResponse.from_parts.return_value

    def test_context_summary_contains_agent_name(self):
        profile = json.dumps({"customer_id": "CUST-123", "first_name": "Jan", "last_name": "de Vries"})
        ctx = CallbackContext(state={
            "_escalation_trigger": "escalate",
            "customer_profile": profile,
            "active_language": "English",
        })
        req = _make_request(_make_user_content("escalate"))
        before_model_callback(ctx, req)
        call_kwargs = python_code.tools.escalate_to_human.call_args[1]
        assert "root_agent" in call_kwargs["context_summary"]

    def test_escalation_survives_tool_exception(self):
        """escalate_to_human raises — callback must still return LlmResponse."""
        python_code.tools.escalate_to_human.side_effect = RuntimeError("service down")
        profile = json.dumps({"customer_id": "X", "first_name": "", "last_name": ""})
        ctx = CallbackContext(state={
            "_escalation_trigger": "escalate",
            "customer_profile": profile,
            "active_language": "English",
        })
        req = _make_request(_make_user_content("escalate"))
        result = before_model_callback(ctx, req)
        assert result is python_code.LlmResponse.from_parts.return_value
        python_code.tools.escalate_to_human.side_effect = None  # reset

    def test_escalation_with_missing_profile_uses_unknown(self):
        ctx = CallbackContext(state={
            "_escalation_trigger": "escalate",
            "customer_profile": "{}",
            "active_language": "English",
        })
        req = _make_request(_make_user_content("escalate"))
        before_model_callback(ctx, req)
        call_kwargs = python_code.tools.escalate_to_human.call_args[1]
        assert call_kwargs["customer_id"] == "UNKNOWN"


# ---------------------------------------------------------------------------
# TestSilenceHandling
# ---------------------------------------------------------------------------
class TestSilenceHandling:
    """Incremental silence counter behaviour."""

    def setup_method(self):
        python_code.tools.reset_mock()
        python_code.LlmResponse.reset_mock()
        python_code.Part.reset_mock()

    def test_first_silence_increments_counter_to_1(self):
        ctx = CallbackContext(state={"_silence_count": "0"})
        req = _make_request(
            _make_model_content("How can I help?"),
            _silence_content(),
        )
        before_model_callback(ctx, req)
        assert ctx.state["_silence_count"] == "1"

    def test_first_silence_returns_llm_response_with_reprompt(self):
        ctx = CallbackContext(state={"_silence_count": "0"})
        req = _make_request(
            _make_model_content("How can I help?"),
            _silence_content(),
        )
        result = before_model_callback(ctx, req)
        python_code.LlmResponse.from_parts.assert_called_once()
        assert result is python_code.LlmResponse.from_parts.return_value
        reprompt_text = python_code.Part.from_text.call_args[1]["text"]
        assert "didn't quite catch" in reprompt_text

    def test_second_silence_increments_counter_to_2(self):
        ctx = CallbackContext(state={"_silence_count": "1"})
        req = _make_request(
            _make_model_content("How can I help?"),
            _silence_content(),
        )
        before_model_callback(ctx, req)
        assert ctx.state["_silence_count"] == "2"

    def test_second_silence_returns_still_cant_hear_reprompt(self):
        ctx = CallbackContext(state={"_silence_count": "1"})
        req = _make_request(
            _make_model_content("How can I help?"),
            _silence_content(),
        )
        before_model_callback(ctx, req)
        reprompt_text = python_code.Part.from_text.call_args[1]["text"]
        assert "still can't hear" in reprompt_text

    def test_third_silence_returns_farewell(self):
        ctx = CallbackContext(state={"_silence_count": "2"})
        req = _make_request(
            _make_model_content("How can I help?"),
            _silence_content(),
        )
        before_model_callback(ctx, req)
        assert ctx.state["_silence_count"] == "3"
        # Part.from_text should mention inability to hear and end_session should fire
        calls = python_code.Part.from_text.call_args_list
        assert len(calls) >= 1
        farewell_text = calls[0][1]["text"]
        assert "unable to hear" in farewell_text.lower() or "unable to hear" in farewell_text

    def test_third_silence_calls_end_session_tool(self):
        python_code.Part.reset_mock()
        ctx = CallbackContext(state={"_silence_count": "2"})
        req = _make_request(
            _make_model_content("How can I help?"),
            _silence_content(),
        )
        before_model_callback(ctx, req)
        python_code.Part.from_function_call.assert_called_once()
        fc_kwargs = python_code.Part.from_function_call.call_args[1]
        assert fc_kwargs["name"] == "end_session"
        assert fc_kwargs["args"]["session_escalated"] is False


# ---------------------------------------------------------------------------
# TestSilenceCounterReset
# ---------------------------------------------------------------------------
class TestSilenceCounterReset:
    """Silence counter resets to 0 when user speaks normally."""

    def setup_method(self):
        python_code.tools.reset_mock()
        python_code.LlmResponse.reset_mock()
        python_code.Part.reset_mock()

    def test_counter_reset_to_zero_on_normal_speech(self):
        ctx = CallbackContext(state={"_silence_count": "2", "_escalation_trigger": ""})
        req = _make_request(
            _make_model_content("How can I help?"),
            _make_user_content("Yes I need help with my WiFi."),
        )
        before_model_callback(ctx, req)
        assert ctx.state["_silence_count"] == "0"

    def test_returns_none_after_counter_reset(self):
        ctx = CallbackContext(state={"_silence_count": "2", "_escalation_trigger": ""})
        req = _make_request(
            _make_model_content("How can I help?"),
            _make_user_content("Yes I need help with my WiFi."),
        )
        result = before_model_callback(ctx, req)
        assert result is None
