"""The representation of a booking: what the API returns and what we store.

These models sit between the domain and both edges deliberately. The document
persisted in ``accommodation_bookings`` is the same document the API returned,
so a booking reads back exactly as it was confirmed -- no second serialisation
format to keep in step, and no risk of a stored quote and a rendered quote
drifting apart.

Every monetary value and rate crosses the wire as a **string** ("120.00"). JSON
numbers are IEEE doubles, and a booking total is not something to hand to a
format that cannot represent 0.1.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, WithJsonSchema

from app.domain.models import (
    Booking,
    BookingRequest,
    Discount,
    Quote,
    RoomLine,
    bill_reference,
)

Money = Annotated[
    Decimal,
    PlainSerializer(lambda value: f"{value:.2f}", return_type=str, when_used="always"),
    WithJsonSchema({"type": "string", "examples": ["120.00"]}),
]

Percent = Annotated[
    Decimal,
    PlainSerializer(
        lambda value: format(value.normalize(), "f"), return_type=str, when_used="always"
    ),
    WithJsonSchema({"type": "string", "examples": ["15"]}),
]


class Schema(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


# --- Request ----------------------------------------------------------------


class AccommodationRequest(Schema):
    """The plain-English lodging request, as typed by the production office."""

    text: str = Field(
        min_length=1,
        max_length=2_000,
        description="The lodging request in plain English.",
        examples=[
            "Book 3 double rooms and 1 suite for 10 nights with half board "
            "for the lead cast and director"
        ],
    )


# --- Parsed request ---------------------------------------------------------


class RoomSelectionOut(Schema):
    room_type: str
    quantity: int


class ParsedRequestOut(Schema):
    """What the parser read out of the text."""

    rooms: tuple[RoomSelectionOut, ...]
    nights: int
    meal_plan: str
    guests: int
    guest_count_source: str = Field(
        description='"stated" when the text gave a headcount, '
        '"derived_from_capacity" when it was inferred from the rooms booked.'
    )
    party: str | None = Field(
        default=None, description='Who the rooms are for, e.g. "the lead cast".'
    )
    warnings: tuple[str, ...] = Field(
        default=(), description="Assumptions the parser had to make."
    )

    @classmethod
    def from_domain(cls, request: BookingRequest) -> ParsedRequestOut:
        return cls(
            rooms=tuple(
                RoomSelectionOut(room_type=room.room_type, quantity=room.quantity)
                for room in request.rooms
            ),
            nights=request.nights,
            meal_plan=request.meal_plan,
            guests=request.guests,
            guest_count_source=request.guest_count_source.value,
            party=request.party,
            warnings=request.warnings,
        )


# --- Quote ------------------------------------------------------------------


class RoomLineOut(Schema):
    """One room type, costed on its own."""

    room_type: str
    category: str
    quantity: int
    capacity_per_room: int
    nightly_rate: Money
    nights: int
    room_charge: Money = Field(description="nightly_rate x nights x quantity")
    guests_allocated: int = Field(description="Guests seated in this room type.")
    meal_rate_per_guest_night: Money
    meal_charge: Money = Field(
        description="meal_rate_per_guest_night x guests_allocated x nights"
    )
    subtotal: Money

    @classmethod
    def from_domain(cls, line: RoomLine) -> RoomLineOut:
        return cls(
            room_type=line.room_type,
            category=line.category,
            quantity=line.quantity,
            capacity_per_room=line.capacity_per_room,
            nightly_rate=line.nightly_rate,
            nights=line.nights,
            room_charge=line.room_charge,
            guests_allocated=line.guests_allocated,
            meal_rate_per_guest_night=line.meal_rate_per_guest_night,
            meal_charge=line.meal_charge,
            subtotal=line.subtotal,
        )


class DiscountOut(Schema):
    applied: bool
    reason: str
    threshold_nights: int
    percent: Percent
    amount: Money

    @classmethod
    def from_domain(cls, discount: Discount) -> DiscountOut:
        return cls(
            applied=discount.applied,
            reason=discount.reason,
            threshold_nights=discount.threshold_nights,
            percent=discount.percent,
            amount=discount.amount,
        )


class QuoteOut(Schema):
    currency: str
    nights: int
    guests: int
    meal_plan: str
    rooms: tuple[RoomLineOut, ...] = Field(description="Cost breakdown per room type.")
    room_subtotal: Money
    meal_subtotal: Money
    subtotal: Money
    discount: DiscountOut
    total: Money

    @classmethod
    def from_domain(cls, quote: Quote) -> QuoteOut:
        return cls(
            currency=quote.currency,
            nights=quote.nights,
            guests=quote.guests,
            meal_plan=quote.meal_plan,
            rooms=tuple(RoomLineOut.from_domain(line) for line in quote.lines),
            room_subtotal=quote.room_subtotal,
            meal_subtotal=quote.meal_subtotal,
            subtotal=quote.subtotal,
            discount=DiscountOut.from_domain(quote.discount),
            total=quote.total,
        )


# --- Booking ----------------------------------------------------------------


class BookingOut(Schema):
    booking_id: str
    reference: str = Field(
        description="The bill reference, e.g. ACM-2026-00042.",
        examples=["ACM-2026-00042"],
    )
    created_at: datetime
    raw_input: str = Field(
        description="The request as it was received, kept verbatim so a bill "
        "always shows the words it was raised from."
    )
    request: ParsedRequestOut
    quote: QuoteOut

    @classmethod
    def from_domain(cls, booking: Booking) -> BookingOut:
        return cls(
            booking_id=booking.id,
            reference=booking.reference,
            created_at=booking.created_at,
            raw_input=booking.raw_input,
            request=ParsedRequestOut.from_domain(booking.request),
            quote=QuoteOut.from_domain(booking.quote),
        )

    @classmethod
    def from_stored(
        cls,
        *,
        booking_id: str,
        bill_number: int,
        created_at: datetime,
        raw_input: str,
        parsed_request: dict[str, Any],
        quote: dict[str, Any],
    ) -> BookingOut:
        """Rebuild a booking from the document that was stored for it."""
        return cls(
            booking_id=booking_id,
            reference=bill_reference(created_at, bill_number),
            created_at=created_at,
            raw_input=raw_input,
            request=ParsedRequestOut.model_validate(parsed_request),
            quote=QuoteOut.model_validate(quote),
        )


class BookingSummaryOut(Schema):
    """The listing view: enough to scan a page of bookings, nothing more."""

    booking_id: str
    reference: str
    created_at: datetime
    raw_input: str
    nights: int
    guests: int
    room_count: int
    meal_plan: str
    currency: str
    total: Money


class BookingPageOut(Schema):
    items: tuple[BookingSummaryOut, ...]
    count: int = Field(description="Total bookings on record, ignoring pagination.")
    limit: int
    offset: int


# --- Errors -----------------------------------------------------------------


class ErrorBody(Schema):
    code: str
    message: str
    hint: str | None = None


class ErrorOut(Schema):
    error: ErrorBody
