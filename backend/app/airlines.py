"""Static metadata about the five loyalty programs the app tracks."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Airline:
    code: str
    name: str
    program: str
    currency: str


AIRLINES: dict[str, Airline] = {
    a.code: a
    for a in (
        Airline("BA", "British Airways", "British Airways Club", "Avios"),
        Airline("AC", "Air Canada", "Aeroplan", "Aeroplan points"),
        Airline("UA", "United", "MileagePlus", "miles"),
        Airline("VS", "Virgin Atlantic", "Flying Club", "Virgin Points"),
        Airline("WN", "Southwest", "Rapid Rewards", "Rapid Rewards points"),
    )
}
