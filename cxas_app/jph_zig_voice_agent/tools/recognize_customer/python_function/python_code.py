def recognize_customer(phone_number: str) -> dict:
    """Looks up a Vodafone Ziggo customer by their inbound telephone number.

    Simulates caller ID lookup against the customer database. Called at session
    start to auto-recognise the inbound caller so the agent can greet them by name.

    Args:
        phone_number: The inbound telephone number (ANI/CLI) in E.164 format,
                      e.g., "+31201234567" (REQUIRED).

    Returns:
        dict with customer_id, first_name, last_name, account_status if found.
        dict with customer_id=null and agent_action if not found.
    """
    # Mock customer database — keyed by E.164 phone number
    _MOCK_DB = {
        "+31201234567": {
            "customer_id": "CZ-98765",
            "first_name": "Jan",
            "last_name": "de Jong",
            "account_status": "Active",
        },
        "+441234567890": {
            "customer_id": "CZ-44321",
            "first_name": "Sarah",
            "last_name": "Jenkins",
            "account_status": "Active",
        },
        "+441987654321": {
            "customer_id": "CZ-12345",
            "first_name": "Mark",
            "last_name": "Evans",
            "account_status": "Active",
        },
    }

    normalised = (phone_number or "").strip()
    customer = _MOCK_DB.get(normalised)

    if customer:
        return customer

    return {
        "customer_id": None,
        "agent_action": (
            "Inform the customer that their number was not recognised "
            "and ask them to confirm their account number."
        ),
    }
