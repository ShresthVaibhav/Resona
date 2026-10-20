"""Symmetric encryption for stored account credentials."""

from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from resona.core.errors import ConfigurationError, UserError

_KEY_HELP = (
    "COOKIE_ENCRYPTION_KEY must be a Fernet key. Generate one with:\n"
    'python -c "from cryptography.fernet import Fernet; '
    'print(Fernet.generate_key().decode())"'
)


class CookieCipher:
    """Encrypts and decrypts cookie headers with Fernet.

    The key never leaves configuration and only ciphertext is persisted.
    """

    def __init__(self, key: str) -> None:
        if not key.strip():
            raise ConfigurationError(
                "Account linking requires COOKIE_ENCRYPTION_KEY.\n" + _KEY_HELP
            )

        try:
            self._fernet = Fernet(key.strip().encode())
        except (ValueError, TypeError) as exc:
            raise ConfigurationError(_KEY_HELP) from exc

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken as exc:
            raise UserError(
                "Stored credentials could not be read. Please link the account "
                "again with /link."
            ) from exc
