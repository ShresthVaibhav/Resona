"""Typed exceptions shared across the project.

``UserError`` (and its subclasses) carry a message that is safe to show to a
Telegram user. Everything else is treated as an internal error and only logged.
"""

from __future__ import annotations


class ResonaError(Exception):
    """Base class for every Resona error."""


class UserError(ResonaError):
    """An error whose message may be shown to the user."""

    default_message = "Something went wrong. Please try again."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.default_message)


class ConfigurationError(ResonaError):
    """Raised when the application is misconfigured."""


class UsageError(UserError):
    """Raised when a command is used with the wrong arguments."""

    default_message = "Invalid usage."

    def __init__(self, message: str | None = None, *, usage: str | None = None) -> None:
        super().__init__(message)
        self.usage = usage


class PermissionDeniedError(UserError):
    default_message = "You are not allowed to use this feature."


class UnavailableError(UserError):
    default_message = "This feature is temporarily unavailable."


class RateLimitedError(UserError):
    default_message = "You are sending commands too quickly. Please slow down."

    def __init__(
        self, message: str | None = None, *, retry_after: float | None = None
    ) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class CredentialsMissingError(UserError):
    default_message = "You have not linked an account yet. Use /link to connect one."


class CredentialsExpiredError(UserError):
    default_message = (
        "Your linked account credentials have expired. Use /link to reconnect."
    )


class DataNotPublicError(UserError):
    """Raised when the game hides a section from the HoYoLAB API."""


class AccountNotFoundError(UserError):
    default_message = "That game account could not be found."


class ExternalAPIError(ResonaError):
    """Raised when an upstream API call fails."""
