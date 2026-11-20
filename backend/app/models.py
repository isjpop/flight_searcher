"""API request and response shapes."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Region = Literal[
    "domestic", "canada", "mexico_caribbean", "central_america", "south_america",
    "europe", "asia", "oceania", "middle_east_africa",
]


class Destination(BaseModel):
    code: str
    city: str
    country: str
    region: Region
    enabled: bool = True


class DestinationCreate(BaseModel):
    code: str = Field(pattern=r"^[A-Za-z]{3}$")
    city: str = Field(min_length=1, max_length=80)
    country: str = Field(min_length=1, max_length=80)
    region: Region
    enabled: bool = True


class DestinationUpdate(BaseModel):
    enabled: bool


class AirlineInfo(BaseModel):
    code: str
    name: str
    program: str
    currency: str
    mode: Literal["mock", "live"]


class CrawlRun(BaseModel):
    airline: str
    mode: str
    status: str
    started_at: str
    finished_at: str | None
    jobs_total: int
    jobs_done: int
    jobs_failed: int
    fares_saved: int
    error: str | None


class CrawlStatus(BaseModel):
    running: bool
    interval_hours: float
    last_finished_at: str | None
    next_due_at: str | None
    runs: list[CrawlRun]


class CrawlRequest(BaseModel):
    airlines: list[str] | None = None


class DealQuery(BaseModel):
    depart_from: date
    return_by: date
    min_nights: int = Field(3, ge=1, le=60)
    max_nights: int = Field(10, ge=1, le=60)
    max_ratio: float = Field(0.7, gt=0, le=1.5)
    airlines: list[str] | None = None
    destinations: list[str] | None = None
    regions: list[Region] | None = None
    mix_programs: bool = False
    max_taxes_usd: float | None = Field(None, ge=0)
    per_destination: int = Field(3, ge=1, le=50)
    limit: int = Field(100, ge=1, le=500)

    @model_validator(mode="after")
    def check_window(self) -> "DealQuery":
        if self.min_nights > self.max_nights:
            raise ValueError("min_nights must be <= max_nights")
        if (self.return_by - self.depart_from).days < self.min_nights:
            raise ValueError("the date window is shorter than min_nights")
        if (self.return_by - self.depart_from).days > 400:
            raise ValueError("the date window can be at most 400 days")
        return self


class Leg(BaseModel):
    airline: str
    origin: str
    destination: str
    date: date
    points: int
    normal_points: int
    ratio: float
    taxes_usd: float
    cabin: str
    fare_brand: str | None
    seats: int | None
    stops: int
    flights: list[str]
    fetched_at: str


class RoundTrip(BaseModel):
    destination: Destination
    outbound: Leg
    inbound: Leg
    nights: int
    ratio: float               # price / normal price; 0.55 means 45% below normal
    savings_pct: float
    points_by_program: dict[str, int]
    normal_points_by_program: dict[str, int]
    taxes_usd: float
    mixed_programs: bool


class DealsResponse(BaseModel):
    results: list[RoundTrip]
    total_matches: int
    data_as_of: str | None
    notes: list[str]
