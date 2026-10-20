"""Repository base class."""

from __future__ import annotations

from typing import Any


class BaseRepository:
    """Wraps a single collection.

    Repositories accept any object exposing the subset of the PyMongo async
    collection API they use, which keeps them testable without a server.
    """

    def __init__(self, collection: Any) -> None:
        self._collection = collection

    @property
    def collection(self) -> Any:
        return self._collection
