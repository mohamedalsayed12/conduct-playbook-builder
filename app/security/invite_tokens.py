"""Invite token generation and hashing (raw token never persisted)."""

import hashlib
import secrets

_TOKEN_BYTES_URLSAFE = 32


def generate_invite_token() -> str:
    """Return a new high-entropy invite token for one-time display to the caller."""
    return secrets.token_urlsafe(_TOKEN_BYTES_URLSAFE)


def hash_invite_token(raw_token: str) -> str:
    """Return the SHA-256 hex digest used for invite lookups."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
