def schedule_mechanic_visit(customer_id: str, preferred_slot: str) -> dict:
    """Books an on-site engineer visit for a Vodafone Ziggo customer.

    Checks engineer availability and confirms the appointment in a single call.
    Returns appointment ID, confirmed date, and time window for the agent to
    relay to the customer.

    Args:
        customer_id: The customer identifier from the customer_profile session
                     variable (e.g., "CZ-44321", "DEMO-001") (REQUIRED).
        preferred_slot: Natural language description of the customer's preferred
                        appointment slot as they expressed it, e.g.,
                        "Next Tuesday morning", "Thursday afternoon",
                        "Any day this week" (REQUIRED).

    Returns:
        dict with appointment_id (str), date (str), time_slot (str), status (str).
        On error: dict with 'error' (str) and 'agent_action' (str).
    """
    _MOCK_APPOINTMENTS = {
        "CZ-44321": {
            "appointment_id": "APT-5544",
            "date": "Next Tuesday",
            "time_slot": "09:00 - 13:00",
            "status": "Confirmed",
        },
        "CZ-12345": {
            "appointment_id": "APT-7788",
            "date": "Next Wednesday",
            "time_slot": "13:00 - 17:00",
            "status": "Confirmed",
        },
        "CZ-98765": {
            "appointment_id": "APT-1010",
            "date": "Next Thursday",
            "time_slot": "09:00 - 13:00",
            "status": "Confirmed",
        },
        "DEMO-001": {
            "appointment_id": "APT-0001",
            "date": "Next Tuesday",
            "time_slot": "09:00 - 13:00",
            "status": "Confirmed",
        },
    }

    cid = (customer_id or "").strip()
    appointment = _MOCK_APPOINTMENTS.get(cid)

    if appointment:
        return appointment

    return {
        "error": "no_slots_available",
        "agent_action": (
            "Apologise to the customer and let them know no available slots were found "
            "at this time. Offer to escalate to a human advisor to manually check the "
            "scheduling system."
        ),
    }
