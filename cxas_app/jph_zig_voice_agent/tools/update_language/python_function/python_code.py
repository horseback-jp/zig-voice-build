def update_language(new_language: str) -> dict:
    """Updates the active conversation language when the customer requests a switch.

    Call this BEFORE generating your first response in the new language.
    Supported languages: "English", "Dutch".

    Args:
        new_language: Language to switch to. One of: "English", "Dutch" (REQUIRED).

    Returns:
        dict with 'success' (bool), 'active_language' (str), 'agent_action' (str).
    """
    _SUPPORTED = {"English", "Dutch"}

    language = (new_language or "").strip()

    if language not in _SUPPORTED:
        return {
            "success": False,
            "active_language": get_variable("active_language", "English"),
            "agent_action": (
                f"Language '{new_language}' is not supported. "
                "Supported languages are: English, Dutch. "
                "Continue in the current language."
            ),
        }

    set_variable("active_language", language)

    return {
        "success": True,
        "active_language": language,
        "agent_action": f"Continue the entire conversation in {language}.",
    }
