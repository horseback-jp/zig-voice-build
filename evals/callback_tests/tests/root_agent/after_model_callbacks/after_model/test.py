"""
Callback tests — root_agent / after_model_callback

Tests cover:
  - No-op: response contains no end_session function call
  - No-op: end_session present but LLM already produced text in this call
  - English farewell injected when end_session present and no prior text
  - Dutch farewell injected when active_language == 'Dutch'
"""

import sys
import os
from unittest.mock import MagicMock, PropertyMock

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__),
    "..", "..", "..", "..", "agents", "root_agent",
    "after_model_callbacks", "after_model",
))

import python_code  # noqa: E402
python_code.LlmResponse = MagicMock()
python_code.Part = MagicMock()

from python_code import after_model_callback  # noqa: E402
from cxas_scrapi.utils.callback_libs import CallbackContext  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_part(has_end_session=False, text=None):
    part = MagicMock()
    part.has_function_call.side_effect = lambda name: (name == "end_session" and has_end_session)
    part.text_or_transcript.return_value = text
    return part


def _make_llm_response(*parts):
    response = MagicMock()
    response.content = MagicMock()
    response.content.parts = list(parts)
    return response


def _make_event(is_agent=False, is_user=False, parts_texts=None):
    event = MagicMock()
    event.is_agent.return_value = is_agent
    event.is_user.return_value = is_user
    if parts_texts:
        event_parts = []
        for t in parts_texts:
            p = MagicMock()
            p.text_or_transcript.return_value = t
            event_parts.append(p)
        event.parts.return_value = event_parts
    else:
        event.parts.return_value = []
    return event


def _ctx_no_prior_text(active_language="English"):
    """Context with no prior agent text events this turn."""
    ctx = CallbackContext(state={"active_language": active_language})
    ctx.events = []
    return ctx


def _ctx_with_prior_text(active_language="English"):
    """Context where a prior agent event already produced text."""
    ctx = CallbackContext(state={"active_language": active_language})
    ctx.events = [_make_event(is_agent=True, parts_texts=["Here is what I found."])]
    return ctx


# ---------------------------------------------------------------------------
# TestNoOpNoEndSession
# ---------------------------------------------------------------------------
class TestNoOpNoEndSession:
    """Response has no end_session — callback must return None."""

    def setup_method(self):
        python_code.LlmResponse.reset_mock()
        python_code.Part.reset_mock()

    def test_returns_none_when_no_end_session(self):
        response = _make_llm_response(
            _make_part(has_end_session=False, text="Your bill is 42 euros."),
        )
        ctx = _ctx_no_prior_text()
        result = after_model_callback(ctx, response)
        assert result is None

    def test_returns_none_for_empty_parts(self):
        response = _make_llm_response()
        ctx = _ctx_no_prior_text()
        result = after_model_callback(ctx, response)
        assert result is None

    def test_no_farewell_injected_without_end_session(self):
        response = _make_llm_response(
            _make_part(has_end_session=False, text="Goodbye for now!"),
        )
        ctx = _ctx_no_prior_text()
        after_model_callback(ctx, response)
        python_code.LlmResponse.from_parts.assert_not_called()


# ---------------------------------------------------------------------------
# TestNoOpTextPresentInCall
# ---------------------------------------------------------------------------
class TestNoOpTextPresentInCall:
    """end_session present but LLM already produced text in the same call — no injection."""

    def setup_method(self):
        python_code.LlmResponse.reset_mock()
        python_code.Part.reset_mock()

    def test_returns_none_when_llm_spoke_before_end_session(self):
        response = _make_llm_response(
            _make_part(has_end_session=False, text="Thank you for calling."),
            _make_part(has_end_session=True, text=None),
        )
        ctx = _ctx_no_prior_text()
        result = after_model_callback(ctx, response)
        assert result is None

    def test_returns_none_when_llm_spoke_after_end_session(self):
        response = _make_llm_response(
            _make_part(has_end_session=True, text=None),
            _make_part(has_end_session=False, text="Take care!"),
        )
        ctx = _ctx_no_prior_text()
        result = after_model_callback(ctx, response)
        assert result is None

    def test_no_farewell_injected_when_text_present_in_call(self):
        response = _make_llm_response(
            _make_part(has_end_session=False, text="Have a nice day!"),
            _make_part(has_end_session=True, text=None),
        )
        ctx = _ctx_no_prior_text()
        after_model_callback(ctx, response)
        python_code.LlmResponse.from_parts.assert_not_called()


# ---------------------------------------------------------------------------
# TestEnglishFarewellInjection
# ---------------------------------------------------------------------------
class TestEnglishFarewellInjection:
    """end_session present, no prior text, active_language == 'English' → English farewell."""

    def setup_method(self):
        python_code.LlmResponse.reset_mock()
        python_code.Part.reset_mock()

    def test_english_farewell_injected(self):
        response = _make_llm_response(
            _make_part(has_end_session=True, text=None),
        )
        ctx = _ctx_no_prior_text(active_language="English")
        result = after_model_callback(ctx, response)
        python_code.LlmResponse.from_parts.assert_called_once()
        assert result is python_code.LlmResponse.from_parts.return_value

    def test_english_farewell_text_content(self):
        response = _make_llm_response(
            _make_part(has_end_session=True, text=None),
        )
        ctx = _ctx_no_prior_text(active_language="English")
        after_model_callback(ctx, response)
        farewell_text = python_code.Part.from_text.call_args[1]["text"]
        assert "Thank you for calling Vodafone Ziggo" in farewell_text

    def test_no_injection_when_prior_agent_event_has_text(self):
        response = _make_llm_response(
            _make_part(has_end_session=True, text=None),
        )
        ctx = _ctx_with_prior_text(active_language="English")
        result = after_model_callback(ctx, response)
        assert result is None

    def test_default_language_fallback_produces_english(self):
        """active_language absent → defaults to English farewell."""
        response = _make_llm_response(
            _make_part(has_end_session=True, text=None),
        )
        ctx = CallbackContext(state={})  # no active_language key
        ctx.events = []
        after_model_callback(ctx, response)
        farewell_text = python_code.Part.from_text.call_args[1]["text"]
        assert "Thank you for calling Vodafone Ziggo" in farewell_text


# ---------------------------------------------------------------------------
# TestDutchFarewellInjection
# ---------------------------------------------------------------------------
class TestDutchFarewellInjection:
    """end_session present, no prior text, active_language == 'Dutch' → Dutch farewell."""

    def setup_method(self):
        python_code.LlmResponse.reset_mock()
        python_code.Part.reset_mock()

    def test_dutch_farewell_injected(self):
        response = _make_llm_response(
            _make_part(has_end_session=True, text=None),
        )
        ctx = _ctx_no_prior_text(active_language="Dutch")
        result = after_model_callback(ctx, response)
        python_code.LlmResponse.from_parts.assert_called_once()
        assert result is python_code.LlmResponse.from_parts.return_value

    def test_dutch_farewell_text_content(self):
        response = _make_llm_response(
            _make_part(has_end_session=True, text=None),
        )
        ctx = _ctx_no_prior_text(active_language="Dutch")
        after_model_callback(ctx, response)
        farewell_text = python_code.Part.from_text.call_args[1]["text"]
        assert "Bedankt voor uw gesprek met Vodafone Ziggo" in farewell_text

    def test_dutch_farewell_not_injected_when_english(self):
        response = _make_llm_response(
            _make_part(has_end_session=True, text=None),
        )
        ctx = _ctx_no_prior_text(active_language="English")
        after_model_callback(ctx, response)
        farewell_text = python_code.Part.from_text.call_args[1]["text"]
        assert "Bedankt" not in farewell_text
