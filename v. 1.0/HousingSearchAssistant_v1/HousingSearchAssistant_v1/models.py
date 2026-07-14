from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

class Decision(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"

@dataclass(frozen=True)
class GeocodeResult:
    address: str
    geocoded_from: str
    latitude: float | None
    longitude: float | None
    status: str
    provider: str = "Nominatim"
