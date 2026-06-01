def get_order_status(customer_id: str) -> dict:
    """Retrieves the most recent hardware order status for a Vodafone Ziggo customer.

    Returns order ID, item name, shipment status, and estimated delivery date
    so the agent can give the customer accurate delivery information.

    Args:
        customer_id: The customer identifier from the customer_profile session
                     variable (e.g., "CZ-98765", "DEMO-001") (REQUIRED).

    Returns:
        dict with order_id (str), item_name (str), status (str), delivery_date (str).
        On error: dict with 'error' (str) and 'agent_action' (str).
    """
    _MOCK_ORDERS = {
        "CZ-98765": {
            "order_id": "ORD-1122",
            "item_name": "Wifi Pod",
            "status": "In Transit",
            "delivery_date": "Tomorrow",
        },
        "CZ-44321": {
            "order_id": "ORD-0987",
            "item_name": "Modem ZG7000",
            "status": "Delivered",
            "delivery_date": "3 days ago",
        },
        "CZ-12345": {
            "order_id": "ORD-2255",
            "item_name": "Wifi Pod",
            "status": "Processing",
            "delivery_date": "In 3 to 5 business days",
        },
        "DEMO-001": {
            "order_id": "ORD-0001",
            "item_name": "Wifi Pod",
            "status": "In Transit",
            "delivery_date": "Tomorrow",
        },
    }

    cid = (customer_id or "").strip()
    order = _MOCK_ORDERS.get(cid)

    if order:
        return order

    return {
        "error": "no_active_order",
        "agent_action": (
            "Inform the customer that no active order was found for their account "
            "and ask if they have an order reference number."
        ),
    }
