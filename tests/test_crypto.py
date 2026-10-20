"""Cookie encryption tests."""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from resona.core.errors import ConfigurationError, UserError
from resona.services.crypto import CookieCipher


def test_round_trip_preserves_plaintext() -> None:
    cipher = CookieCipher(Fernet.generate_key().decode())

    token = cipher.encrypt("ltuid_v2=1; ltoken_v2=secret")

    assert "secret" not in token
    assert cipher.decrypt(token) == "ltuid_v2=1; ltoken_v2=secret"


def test_empty_key_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="COOKIE_ENCRYPTION_KEY"):
        CookieCipher("   ")


def test_malformed_key_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="Fernet key"):
        CookieCipher("not-a-fernet-key")


def test_wrong_key_cannot_decrypt() -> None:
    first = CookieCipher(Fernet.generate_key().decode())
    second = CookieCipher(Fernet.generate_key().decode())
    token = first.encrypt("payload")

    with pytest.raises(UserError, match="could not be read"):
        second.decrypt(token)
