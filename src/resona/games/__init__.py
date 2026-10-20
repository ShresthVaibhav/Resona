"""Game integrations.

Game modules are added in a later milestone. This package currently only holds
the identifier mapping used by the shared services.
"""

from __future__ import annotations

from resona.games.mapping import (
    business_ids,
    library_game,
    library_lang,
    region_from_business_id,
)

__all__ = [
    "business_ids",
    "library_game",
    "library_lang",
    "region_from_business_id",
]
