def get_modem_diagnostics(customer_id: str) -> dict:
    """Retrieves modem telemetry and area outage status for a Vodafone Ziggo customer.

    Returns a combined diagnostic snapshot: modem online status, signal strength,
    packet loss level, and area outage flag. Use this to perform a complete
    diagnostic without requiring multiple tool calls.

    Args:
        customer_id: The customer identifier from the customer_profile session
                     variable (e.g., "CZ-44321", "DEMO-001") (REQUIRED).

    Returns:
        dict with modem_id (str), status (str), signal_strength (str),
        packet_loss (str), area_outage (bool).
        On error: dict with 'error' (str) and 'agent_action' (str).
    """
    _MOCK_DIAGNOSTICS = {
        "CZ-98765": {
            "modem_id": "MOD-3301",
            "status": "Online",
            "signal_strength": "Good",
            "packet_loss": "Low",
            "area_outage": False,
        },
        "CZ-44321": {
            "modem_id": "MOD-8812",
            "status": "Online",
            "signal_strength": "Weak",
            "packet_loss": "High",
            "area_outage": False,
        },
        "CZ-12345": {
            "modem_id": "MOD-6655",
            "status": "Online",
            "signal_strength": "Weak",
            "packet_loss": "High",
            "area_outage": False,
        },
        "DEMO-001": {
            "modem_id": "MOD-0001",
            "status": "Online",
            "signal_strength": "Weak",
            "packet_loss": "High",
            "area_outage": False,
        },
    }

    cid = (customer_id or "").strip()
    diag = _MOCK_DIAGNOSTICS.get(cid)

    if diag:
        return diag

    return {
        "error": "diagnostics_unavailable",
        "agent_action": (
            "Apologise and note that remote diagnostics are temporarily unavailable. "
            "Offer to schedule a mechanic visit directly to resolve the issue on-site."
        ),
    }
