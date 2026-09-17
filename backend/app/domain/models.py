"""Immutable value objects passed between the parser, the pricer and the API.

Keeping these as plain frozen dataclasses (rather than Pydantic models) keeps the
domain independent of the transport layer: the API owns its own schemas and maps
onto these, so a change to the wire format never forces a change to the rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from app.domain.catalog import MealPlanName, RoomCategory, RoomTypeName


class GuestCountSource(StrEnum):
    """Where the guest count in a booking came from."""

    #: The request said so ("for 6 people").
    STATED = "stated"
    #: Nobody said, so we assumed the rooms are filled to capacity.
    DERIVED_FROM_CAPACITY = "derived_from_capacity"


@dataclass(frozen=True, slots=True)
class RoomSelection:
    room_type: RoomTypeName
    quantity: int


@dataclass(frozen=True, slots=True)
class BookingRequest:
    """A lodging request after it has been read out of free text."""

    rooms: tuple[RoomSelection, ...]
    nights: int
    meal_plan: MealPlanName
    guests: int
    guest_count_source: GuestCountSource
    #: Who the rooms are for, verbatim from the request ("the lead cast and director").
    party: str | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def total_rooms(self) -> int:
        return sum(room.quantity for room in self.rooms)


@dataclass(frozen=True, slots=True)
class RoomLine:
    """One room type's share of a quote, costed on its own."""

    room_type: RoomTypeName
    category: RoomCategory
    quantity: int
    nightly_rate: Decimal
    capacity_per_room: int
    nights: int
    room_charge: Decimal
    guests_allocated: int
    meal_rate_per_guest_night: Decimal
    meal_charge: Decimal
    subtotal: Decimal


@dataclass(frozen=True, slots=True)
class Discount:
    applied: bool
    reason: str
    threshold_nights: int
    percent: Decimal
    amount: Decimal


@dataclass(frozen=True, slots=True)
class Quote:
    currency: str
    nights: int
    guests: int
    meal_plan: MealPlanName
    lines: tuple[RoomLine, ...]
    room_subtotal: Decimal
    meal_subtotal: Decimal
    subtotal: Decimal
    discount: Discount
    total: Decimal


#: Prefix on every bill reference. Short, and unmistakable on a printed page.
BILL_PREFIX = "ACM"


def bill_reference(issued: datetime, bill_number: int) -> str:
    """The reference a person reads off a bill: ``ACM-2026-00042``."""
    return f"{BILL_PREFIX}-{issued.year}-{bill_number:05d}"


@dataclass(frozen=True, slots=True)
class Booking:
    """A confirmed booking: the request as received, and the price it was held at."""

    id: str
    #: Sequential across the whole ledger; what makes the booking a bill.
    bill_number: int
    created_at: datetime
    raw_input: str
    request: BookingRequest
    quote: Quote

    @property
    def reference(self) -> str:
        return bill_reference(self.created_at, self.bill_number)
