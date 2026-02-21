def get_scoreable_text(user_content: str, assistant_content: str) -> str:
    """Combine user and assistant content into a single string for embedding/scoring."""
    parts = []
    if user_content:
        parts.append(user_content)
    if assistant_content:
        parts.append(assistant_content)
    return " ".join(parts)
