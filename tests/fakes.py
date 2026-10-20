"""In-memory doubles for the PyMongo async collection API.

Only the operations Resona repositories actually use are implemented, which
keeps repository tests runnable without a MongoDB server.
"""

from __future__ import annotations

import copy
from types import SimpleNamespace
from typing import Any

from pymongo.errors import DuplicateKeyError


def _matches(document: dict[str, Any], query: dict[str, Any]) -> bool:
    for key, expected in query.items():
        if document.get(key) != expected:
            return False
    return True


class FakeCursor:
    def __init__(self, documents: list[dict[str, Any]]) -> None:
        self._documents = documents

    def sort(self, key: Any, direction: int = 1) -> FakeCursor:
        if isinstance(key, list):
            for field, order in reversed(key):
                self._documents.sort(
                    key=lambda doc, field=field: doc.get(field), reverse=order == -1
                )
        else:
            self._documents.sort(key=lambda doc: doc.get(key), reverse=direction == -1)
        return self

    def limit(self, count: int) -> FakeCursor:
        if count:
            self._documents = self._documents[:count]
        return self

    async def to_list(self, length: int | None = None) -> list[dict[str, Any]]:
        items = self._documents if length is None else self._documents[:length]
        return [copy.deepcopy(document) for document in items]


class FakeCollection:
    def __init__(self, unique_keys: list[tuple[str, ...]] | None = None) -> None:
        self.documents: list[dict[str, Any]] = []
        self.unique_keys: list[tuple[str, ...]] = list(unique_keys or [])
        self.indexes: list[tuple[Any, dict[str, Any]]] = []

    # -- indexes -------------------------------------------------------------
    async def create_index(self, keys: Any, **kwargs: Any) -> str:
        self.indexes.append((keys, kwargs))
        if kwargs.get("unique"):
            normalized = [(keys, 1)] if isinstance(keys, str) else list(keys)
            self.unique_keys.append(tuple(field for field, _ in normalized))
        return f"index_{len(self.indexes)}"

    # -- reads ---------------------------------------------------------------
    async def find_one(
        self,
        query: dict[str, Any] | None = None,
        projection: Any = None,
        sort: Any = None,
    ) -> dict[str, Any] | None:
        for document in self.documents:
            if _matches(document, query or {}):
                return copy.deepcopy(document)
        return None

    def find(
        self, query: dict[str, Any] | None = None, projection: Any = None
    ) -> FakeCursor:
        matches = [
            document for document in self.documents if _matches(document, query or {})
        ]
        return FakeCursor(matches)

    async def count_documents(self, query: dict[str, Any] | None = None) -> int:
        return sum(1 for document in self.documents if _matches(document, query or {}))

    # -- writes --------------------------------------------------------------
    async def insert_one(self, document: dict[str, Any]) -> SimpleNamespace:
        if self._conflicts(document):
            raise DuplicateKeyError("duplicate key error")
        self.documents.append(copy.deepcopy(document))
        return SimpleNamespace(inserted_id=len(self.documents))

    async def update_one(
        self,
        query: dict[str, Any],
        update: dict[str, Any],
        upsert: bool = False,
    ) -> SimpleNamespace:
        for document in self.documents:
            if _matches(document, query):
                self._apply(document, update)
                return SimpleNamespace(
                    matched_count=1, modified_count=1, upserted_id=None
                )

        if not upsert:
            return SimpleNamespace(matched_count=0, modified_count=0, upserted_id=None)

        document = {
            key: value for key, value in query.items() if not isinstance(value, dict)
        }
        self._apply(document, update)
        if self._conflicts(document):
            raise DuplicateKeyError("duplicate key error")
        self.documents.append(document)
        return SimpleNamespace(
            matched_count=0, modified_count=0, upserted_id=len(self.documents)
        )

    async def update_many(
        self, query: dict[str, Any], update: dict[str, Any]
    ) -> SimpleNamespace:
        matched = 0
        for document in self.documents:
            if _matches(document, query):
                self._apply(document, update)
                matched += 1
        return SimpleNamespace(matched_count=matched, modified_count=matched)

    async def delete_one(self, query: dict[str, Any]) -> SimpleNamespace:
        for index, document in enumerate(self.documents):
            if _matches(document, query):
                self.documents.pop(index)
                return SimpleNamespace(deleted_count=1)
        return SimpleNamespace(deleted_count=0)

    async def delete_many(self, query: dict[str, Any]) -> SimpleNamespace:
        keep = [d for d in self.documents if not _matches(d, query)]
        removed = len(self.documents) - len(keep)
        self.documents = keep
        return SimpleNamespace(deleted_count=removed)

    # -- helpers -------------------------------------------------------------
    def _apply(self, document: dict[str, Any], update: dict[str, Any]) -> None:
        for key, value in update.get("$set", {}).items():
            document[key] = value
        for key, value in update.get("$setOnInsert", {}).items():
            document.setdefault(key, value)

    def _conflicts(self, document: dict[str, Any]) -> bool:
        for keys in self.unique_keys:
            if not all(key in document for key in keys):
                continue
            for existing in self.documents:
                if all(existing.get(key) == document.get(key) for key in keys):
                    return True
        return False


class FakeDatabase:
    def __init__(self, name: str = "resona") -> None:
        self.name = name
        self.collections: dict[str, FakeCollection] = {}

    def __getitem__(self, name: str) -> FakeCollection:
        return self.collections.setdefault(name, FakeCollection())


class FakeMongoClient:
    """Stand-in for ``pymongo.AsyncMongoClient``."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.args = args
        self.kwargs = kwargs
        self.databases: dict[str, FakeDatabase] = {}
        self.pinged = False
        self.closed = False

        async def _command(*_args: Any, **_kwargs: Any) -> dict[str, int]:
            self.pinged = True
            return {"ok": 1}

        self.admin = SimpleNamespace(command=_command)

    def __getitem__(self, name: str) -> FakeDatabase:
        return self.databases.setdefault(name, FakeDatabase(name))

    async def close(self) -> None:
        self.closed = True
