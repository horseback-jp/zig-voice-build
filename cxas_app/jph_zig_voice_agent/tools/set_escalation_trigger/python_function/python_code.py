def set_escalation_trigger(reason: str) -> dict:
    """Sets the escalation trigger in session state to signal a required human transfer.

    Call this when the customer requests a human agent, the issue is unresolvable,
    or the request is out of scope. The before_model_callback will intercept the
    trigger on the next model call and execute escalate_to_human deterministically.

    Do NOT call escalate_to_human directly — use this tool to signal intent.
    After calling this tool, do not say anything further.

    Args:
        reason: Brief reason for escalation. One of: "customer_requested",
                "unresolvable", "out_of_scope", "billing_unavailable",
                "scheduling_unavailable", "unrecognised_customer" (REQUIRED).

    Returns:
        dict with 'trigger_set' (bool) and 'agent_action' (str).
    """
    set_variable("_escalation_trigger", "escalate")
    set_variable("_escalation_reason", reason)

    return {
        "trigger_set": True,
        "agent_action": (
            "The escalation trigger has been set. "
            "Do not say anything further — the transfer will be handled automatically."
        ),
    }
