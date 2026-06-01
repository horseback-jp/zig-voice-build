"""
Callback tests — billing_and_order_agent / before_model_callback

Tests cover:
  - No-op path: _escalation_trigger empty → returns None
  - Escalation trigger fires: trigger cleared, escalate_to_human called,
    LlmResponse returned with billing context summary
"""

import sys
import os
import json
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "..", "agents", "billing_and_order_agent",
    "before_model_callbacks", "before_model",
))

import python_code  # noqa: E402
python_code.tools = MagicMock()
python_code.LlmResponse = MagicMock()
python_code.Part = MagicMock()

from python_code import before_model_callback  # noqa: E402
from cxas_scrapi.utils.callback_libs import CallbackContext  # noqa: E402


def _make_request():
    req = MagicMock()
    req.contents = []
    return req


# ---------------------------------------------------------------------------
# TestNoOpPath
# ---------------------------------------------------------------------------
class TestNoOpPath:
    """No escalation trigger — callback must return None without side effects."""

    def setup_method(self):
        python_code.tools.reset_mock()
        python_code.LlmResponse.reset_mock()

    def test_returns_none_when_trigger_empty(self):
        ctx = CallbackContext(state={"_escalation_trigger": ""})
        result = before_model_callback(ctx, _make_request())
        assert result is None

    def test_returns_none_when_trigger_absent(self):
        ctx = CallbackContext(state={})
        result = before_model_callback(ctx, _make_request())
        assert result is None

    def test_escalate_to_human_not_called_on_no_op(self):
        ctx = CallbackContext(state={})
        before_model_callback(ctx, _make_request())
        python_code.tools.escalate_to_human.assert_not_called()

    def test_trigger_not_modified_on_no_op(self):
        ctx = CallbackContext(state={"_escalation_trigger": ""})
        before_model_callback(ctx, _make_request())
        assert ctx.state["_escalation_trigger"] == ""


# ---------------------------------------------------------------------------
# TestEscalationTrigger
# ---------------------------------------------------------------------------
class TestEscalationTrigger:
    """_escalation_trigger == 'escalate' → billing escalation fired."""

    def setup_method(self):
        python_code.tools.reset_mock()
        python_code.LlmResponse.reset_mock()
        python_code.Part.reset_mock()

    def _billing_state(self, customer_id="CUST-456", first_name="Fatima", last_name="Yilmaz"):
        profile = json.dumps({
            "customer_id": customer_id,
            "first_name": first_name,
            "last_name": last_name,
        })
        return {
            "_escalation_trigger": "escalate",
            "customer_profile": profile,
            "active_language": "English",
        }

    def test_trigger_cleared_after_escalation(self):
        ctx = CallbackContext(state=self._billing_state())
        before_model_callback(ctx, _make_request())
        assert ctx.state["_escalation_trigger"] == ""

    def test_escalate_to_human_called_once(self):
        ctx = CallbackContext(state=self._billing_state())
        before_model_callback(ctx, _make_request())
        python_code.tools.escalate_to_human.assert_called_once()

    def test_escalate_to_human_receives_correct_customer_id(self):
        ctx = CallbackContext(state=self._billing_state(customer_id="CUST-456"))
        before_model_callback(ctx, _make_request())
        call_kwargs = python_code.tools.escalate_to_human.call_args[1]
        assert call_kwargs["customer_id"] == "CUST-456"

    def test_context_summary_references_billing_agent(self):
        ctx = CallbackContext(state=self._billing_state())
        before_model_callback(ctx, _make_request())
        call_kwargs = python_code.tools.escalate_to_human.call_args[1]
        assert "billing_and_order_agent" in call_kwargs["context_summary"]

    def test_context_summary_mentions_billing_domain(self):
        ctx = CallbackContext(state=self._billing_state())
        before_model_callback(ctx, _make_request())
        call_kwargs = python_code.tools.escalate_to_human.call_args[1]
        summary = call_kwargs["context_summary"].lower()
        assert "billing" in summary or "order" in summary

    def test_llm_response_returned(self):
        ctx = CallbackContext(state=self._billing_state())
        result = before_model_callback(ctx, _make_request())
        python_code.LlmResponse.from_parts.assert_called_once()
        assert result is python_code.LlmResponse.from_parts.return_value

    def test_response_text_mentions_billing_advisor(self):
        ctx = CallbackContext(state=self._billing_state())
        before_model_callback(ctx, _make_request())
        text = python_code.Part.from_text.call_args[1]["text"]
        assert "billing" in text.lower()

    def test_end_session_function_call_included(self):
        ctx = CallbackContext(state=self._billing_state())
        before_model_callback(ctx, _make_request())
        python_code.Part.from_function_call.assert_called_once()
        fc_kwargs = python_code.Part.from_function_call.call_args[1]
        assert fc_kwargs["name"] == "end_session"
        assert fc_kwargs["args"]["session_escalated"] is True

    def test_escalation_survives_tool_exception(self):
        python_code.tools.escalate_to_human.side_effect = RuntimeError("timeout")
        ctx = CallbackContext(state=self._billing_state())
        result = before_model_callback(ctx, _make_request())
        assert result is python_code.LlmResponse.from_parts.return_value
        python_code.tools.escalate_to_human.side_effect = None

    def test_missing_customer_profile_uses_unknown(self):
        ctx = CallbackContext(state={
            "_escalation_trigger": "escalate",
            "customer_profile": "{}",
            "active_language": "English",
        })
        before_model_callback(ctx, _make_request())
        call_kwargs = python_code.tools.escalate_to_human.call_args[1]
        assert call_kwargs["customer_id"] == "UNKNOWN"
