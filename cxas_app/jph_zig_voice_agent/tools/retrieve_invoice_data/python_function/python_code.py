def retrieve_invoice_data(customer_id: str) -> dict:
    """Retrieves billing variance data for a Vodafone Ziggo customer.

    Returns current and previous invoice totals plus itemised charges so the agent
    can explain any increase or unexpected line items to the customer.

    Args:
        customer_id: The customer identifier from the customer_profile session
                     variable (e.g., "CZ-98765", "DEMO-001") (REQUIRED).

    Returns:
        dict with current_bill (float), previous_bill (float), itemized_charges (list).
        On error: dict with 'error' (str) and 'agent_action' (str).
    """
    _MOCK_BILLING = {
        "CZ-98765": {
            "current_bill": 75.00,
            "previous_bill": 60.00,
            "itemized_charges": [
                {"item": "Broadband (500 Mbps)", "cost": 45.00},
                {"item": "TV Package (Standard)", "cost": 15.00},
                {"item": "Wifi Pod (Monthly fee)", "cost": 15.00},
            ],
        },
        "CZ-44321": {
            "current_bill": 55.00,
            "previous_bill": 55.00,
            "itemized_charges": [
                {"item": "Broadband (250 Mbps)", "cost": 35.00},
                {"item": "TV Package (Basic)", "cost": 20.00},
            ],
        },
        "CZ-12345": {
            "current_bill": 90.00,
            "previous_bill": 75.00,
            "itemized_charges": [
                {"item": "Broadband (1 Gbps)", "cost": 60.00},
                {"item": "TV Package (Premium)", "cost": 15.00},
                {"item": "Wifi Pod (Monthly fee)", "cost": 15.00},
            ],
        },
        "DEMO-001": {
            "current_bill": 65.00,
            "previous_bill": 50.00,
            "itemized_charges": [
                {"item": "Broadband (500 Mbps)", "cost": 45.00},
                {"item": "TV Package (Standard)", "cost": 15.00},
                {"item": "Paper Billing fee", "cost": 5.00},
            ],
        },
    }

    cid = (customer_id or "").strip()
    data = _MOCK_BILLING.get(cid)

    if data:
        return data

    return {
        "error": "billing_unavailable",
        "agent_action": (
            "Apologise to the customer and let them know billing data is temporarily "
            "unavailable. Offer to escalate to a billing specialist."
        ),
    }
