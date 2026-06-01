def escalate_to_human(customer_id: str, context_summary: str) -> dict:
    """Packages session context and triggers a warm transfer to a live agent queue.

    This tool is called by the before_model_callback — NOT directly by the LLM.
    To request escalation from instructions, call set_escalation_trigger instead.

    Args:
        customer_id: The customer identifier from the customer_profile session
                     variable (e.g., "CZ-44321", "DEMO-001") (REQUIRED).
        context_summary: Free-text summary of what was resolved, the customer's
                         issue, and the reason for the transfer. Must be
                         non-empty so the receiving agent has context (REQUIRED).

    Returns:
        dict with transfer_status (str) and target_queue (str).
    """
    # In a production implementation this would call a CTI/WFM API.
    # For demo, simulate a successful transfer.

    cid = (customer_id or "").strip() or "UNKNOWN"
    summary = (context_summary or "").strip() or "No summary provided."

    if not cid or cid == "UNKNOWN":
        return {
            "error": "missing_customer_id",
            "agent_action": (
                "The escalation could not be completed because no customer ID was available. "
                "Apologise to the customer and ask them to confirm their account number, "
                "then retry the escalation."
            ),
        }

    # Log for observability (platform captures stdout from tool execution)
    print(f"[escalate_to_human] customer_id={cid} | summary={summary[:200]}")

    return {
        "transfer_status": "Success",
        "target_queue": "Level_2_Support",
    }
