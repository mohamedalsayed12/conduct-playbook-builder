"""Argon2 password hashing."""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Return an argon2 hash of the given password."""
    return _password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Return True when the password matches the stored hash."""
    try:
        return _password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False
