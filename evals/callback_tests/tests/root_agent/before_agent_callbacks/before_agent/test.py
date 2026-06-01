"""
Callback tests — root_agent / before_agent_callback

Tests cover:
  - Early return when customer_profile already in state
  - Successful ANI recognition (known caller)
  - Default persona when telephony-caller-id is absent
  - Unrecognised number (recognize_customer returns null customer_id)
  - Tool call failure → default persona fallback
"""

import sys
import os
import json
from unittest.mock import MagicMock, call

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "..", "agents", "root_agent",
    "before_agent_callbacks", "before_agent",
))

import python_code  # noqa: E402
python_code.tools = MagicMock()
python_code.LlmResponse = MagicMock()
python_code.Part = MagicMock()

from python_code import before_agent_callback  # noqa: E402
from cxas_scrapi.utils.callback_libs import CallbackContext  # noqa: E402


# ---------------------------------------------------------------------------
# TestEarlyReturn
# ---------------------------------------------------------------------------
class TestEarlyReturn:
    """customer_profile already set — callback must not re-process."""

    def test_returns_none_when_customer_profile_present(self):
        ctx = CallbackContext(state={"customer_profile": '{"customer_id": "123"}'})
        result = before_agent_callback(ctx)
        assert result is None

    def test_does_not_call_recognize_customer_on_re_entry(self):
        python_code.tools.recognize_customer.reset_mock()
        ctx = CallbackContext(state={"customer_profile": '{"customer_id": "123"}'})
        before_agent_callback(ctx)
        python_code.tools.recognize_customer.assert_not_called()

    def test_does_not_overwrite_existing_state(self):
        state = {
            "customer_profile": '{"customer_id": "123"}',
            "active_language": "Dutch",
        }
        ctx = CallbackContext(state=state)
        before_agent_callback(ctx)
        assert ctx.state["active_language"] == "Dutch"


# ---------------------------------------------------------------------------
# TestSuccessfulRecognition
# ---------------------------------------------------------------------------
class TestSuccessfulRecognition:
    """telephony-caller-id present and recognize_customer returns a known customer."""

    def setup_method(self):
        python_code.tools.recognize_customer.reset_mock()
        python_code.LlmResponse.reset_mock()
        python_code.Part.reset_mock()
        python_code.tools.recognize_customer.return_value = {
            "customer_id": "CUST-999",
            "first_name": "Sophie",
            "last_name": "Jansen",
            "account_status": "Active",
        }

    def test_calls_recognize_customer_with_phone_number(self):
        ctx = CallbackContext(state={"telephony-caller-id": "+31612345678"})
        before_agent_callback(ctx)
        python_code.tools.recognize_customer.assert_called_once_with(
            phone_number="+31612345678"
        )

    def test_customer_profile_written_to_state(self):
        ctx = CallbackContext(state={"telephony-caller-id": "+31612345678"})
        before_agent_callback(ctx)
        profile = json.loads(ctx.state["customer_profile"])
        assert profile["customer_id"] == "CUST-999"
        assert profile["first_name"] == "Sophie"
        assert profile["last_name"] == "Jansen"
        assert profile["account_status"] == "Active"
        assert profile["is_default_persona"] is False

    def test_active_language_set_to_english(self):
        ctx = CallbackContext(state={"telephony-caller-id": "+31612345678"})
        before_agent_callback(ctx)
        assert ctx.state["active_language"] == "English"

    def test_deterministic_greeting_returned(self):
        ctx = CallbackContext(state={"telephony-caller-id": "+31612345678"})
        before_agent_callback(ctx)
        # Part.from_text should have been called with the personalised greeting
        python_code.Part.from_text.assert_called_once()
        greeting_text = python_code.Part.from_text.call_args[1]["text"]
        assert "Sophie Jansen" in greeting_text
        assert "automatically recognised" in greeting_text

    def test_llm_response_constructed(self):
        ctx = CallbackContext(state={"telephony-caller-id": "+31612345678"})
        result = before_agent_callback(ctx)
        python_code.LlmResponse.from_parts.assert_called_once()
        # Result is whatever LlmResponse.from_parts returns
        assert result is python_code.LlmResponse.from_parts.return_value


# ---------------------------------------------------------------------------
# TestDefaultPersonaFallback
# ---------------------------------------------------------------------------
class TestDefaultPersonaFallback:
    """telephony-caller-id absent — default demo persona must be used."""

    def setup_method(self):
        python_code.tools.recognize_customer.reset_mock()
        python_code.LlmResponse.reset_mock()
        python_code.Part.reset_mock()

    def test_recognize_customer_not_called_when_no_ani(self):
        ctx = CallbackContext(state={})
        before_agent_callback(ctx)
        python_code.tools.recognize_customer.assert_not_called()

    def test_default_persona_written_to_state(self):
        ctx = CallbackContext(state={})
        before_agent_callback(ctx)
        profile = json.loads(ctx.state["customer_profile"])
        assert profile["customer_id"] == "DEMO-001"
        assert profile["is_default_persona"] is True

    def test_active_language_set_to_english(self):
        ctx = CallbackContext(state={})
        before_agent_callback(ctx)
        assert ctx.state["active_language"] == "English"

    def test_generic_greeting_returned(self):
        ctx = CallbackContext(state={})
        before_agent_callback(ctx)
        greeting_text = python_code.Part.from_text.call_args[1]["text"]
        assert "How can I help you today?" in greeting_text

    def test_llm_response_returned(self):
        ctx = CallbackContext(state={})
        result = before_agent_callback(ctx)
        python_code.LlmResponse.from_parts.assert_called_once()
        assert result is python_code.LlmResponse.from_parts.return_value


# ---------------------------------------------------------------------------
# TestUnrecognisedNumber
# ---------------------------------------------------------------------------
class TestUnrecognisedNumber:
    """recognize_customer returns a result with no customer_id → default persona."""

    def setup_method(self):
        python_code.tools.recognize_customer.reset_mock()
        python_code.LlmResponse.reset_mock()
        python_code.Part.reset_mock()
        python_code.tools.recognize_customer.return_value = {"customer_id": None}

    def test_default_persona_used_when_no_customer_id(self):
        ctx = CallbackContext(state={"telephony-caller-id": "+31699999999"})
        before_agent_callback(ctx)
        profile = json.loads(ctx.state["customer_profile"])
        assert profile["customer_id"] == "DEMO-001"
        assert profile["is_default_persona"] is True

    def test_generic_greeting_returned_for_unrecognised(self):
        ctx = CallbackContext(state={"telephony-caller-id": "+31699999999"})
        before_agent_callback(ctx)
        greeting_text = python_code.Part.from_text.call_args[1]["text"]
        assert "How can I help you today?" in greeting_text


# ---------------------------------------------------------------------------
# TestToolCallFailure
# ---------------------------------------------------------------------------
class TestToolCallFailure:
    """recognize_customer raises an exception → default persona fallback."""

    def setup_method(self):
        python_code.tools.recognize_customer.reset_mock()
        python_code.LlmResponse.reset_mock()
        python_code.Part.reset_mock()
        python_code.tools.recognize_customer.side_effect = RuntimeError("API timeout")

    def test_default_persona_used_on_exception(self):
        ctx = CallbackContext(state={"telephony-caller-id": "+31611111111"})
        before_agent_callback(ctx)
        profile = json.loads(ctx.state["customer_profile"])
        assert profile["customer_id"] == "DEMO-001"
        assert profile["is_default_persona"] is True

    def test_active_language_still_set_after_exception(self):
        ctx = CallbackContext(state={"telephony-caller-id": "+31611111111"})
        before_agent_callback(ctx)
        assert ctx.state["active_language"] == "English"

    def test_generic_greeting_returned_after_exception(self):
        ctx = CallbackContext(state={"telephony-caller-id": "+31611111111"})
        before_agent_callback(ctx)
        greeting_text = python_code.Part.from_text.call_args[1]["text"]
        assert "How can I help you today?" in greeting_text
