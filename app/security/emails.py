"""Email normalization helpers."""


def normalize_email(email: str) -> str:
    """Return a trimmed, lowercased email for storage and lookup."""
    return email.strip().lower()
