"""Use cases: take a request in, hand a stored bill back.

This is the only place the three halves of the system meet -- the parser, the
pricer and the database -- and it is deliberately thin. All the judgement lives
in the domain; all the SQL lives in the repository.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import BookingRecord
from app.db.repository import BookingRepository
from app.domain.errors import BookingNotFound
from app.domain.models import Booking, bill_reference
from app.domain.pricing import quote as price
from app.parsing.parser import parse
from app.schemas import BookingOut, BookingPageOut, BookingSummaryOut

logger = logging.getLogger(__name__)

MAX_PAGE_SIZE = 100

#: Two writers can read the same highest bill number before either commits. The
#: unique constraint catches it; this is how many times the loser tries again.
BILL_NUMBER_ATTEMPTS = 5


def create_booking(session: Session, text: str) -> BookingOut:
    """Parse ``text``, price it, store it, and return the confirmed bill.

    Raises:
        BookingError: the text could not be read, or asks for something
            that cannot be booked. Nothing is written in that case.
    """
    request = parse(text)
    quote = price(request)
    repository = BookingRepository(session)

    for attempt in range(1, BILL_NUMBER_ATTEMPTS + 1):
        booking = Booking(
            id=str(uuid4()),
            bill_number=repository.next_bill_number(),
            created_at=datetime.now(UTC),
            raw_input=text.strip(),
            request=request,
            quote=quote,
        )
        document = BookingOut.from_domain(booking)

        try:
            # A savepoint, so a collision on the bill number does not take the
            # surrounding request transaction down with it.
            with session.begin_nested():
                repository.add(_to_record(booking, document))
        except IntegrityError:
            if attempt == BILL_NUMBER_ATTEMPTS:
                raise
            logger.warning(
                "Bill number %s was taken; retrying (attempt %s).",
                booking.bill_number,
                attempt,
            )
            continue

        return document

    raise AssertionError("unreachable: the loop either returns or raises")


def get_booking(session: Session, booking_id: str) -> BookingOut:
    record = BookingRepository(session).get(booking_id)
    if record is None:
        raise BookingNotFound(booking_id)
    return _to_document(record)


def list_bookings(session: Session, *, limit: int, offset: int) -> BookingPageOut:
    records, total = BookingRepository(session).page(limit=limit, offset=offset)
    return BookingPageOut(
        items=tuple(_to_summary(record) for record in records),
        count=total,
        limit=limit,
        offset=offset,
    )


def _to_record(booking: Booking, document: BookingOut) -> BookingRecord:
    return BookingRecord(
        id=booking.id,
        bill_number=booking.bill_number,
        created_at=booking.created_at,
        raw_input=booking.raw_input,
        parsed_request=document.request.model_dump(mode="json"),
        quote=document.quote.model_dump(mode="json"),
        currency=booking.quote.currency,
        total_cents=_to_cents(booking.quote.total),
        nights=booking.request.nights,
        guests=booking.request.guests,
        room_count=booking.request.total_rooms,
        meal_plan=booking.request.meal_plan,
    )


def _to_document(record: BookingRecord) -> BookingOut:
    return BookingOut.from_stored(
        booking_id=record.id,
        bill_number=record.bill_number,
        created_at=_as_utc(record.created_at),
        raw_input=record.raw_input,
        parsed_request=record.parsed_request,
        quote=record.quote,
    )


def _to_summary(record: BookingRecord) -> BookingSummaryOut:
    created_at = _as_utc(record.created_at)
    return BookingSummaryOut(
        booking_id=record.id,
        reference=bill_reference(created_at, record.bill_number),
        created_at=created_at,
        raw_input=record.raw_input,
        nights=record.nights,
        guests=record.guests,
        room_count=record.room_count,
        meal_plan=record.meal_plan,
        currency=record.currency,
        total=Decimal(record.total_cents) / 100,
    )


def _to_cents(amount: Decimal) -> int:
    return int((amount * 100).to_integral_value())


def _as_utc(moment: datetime) -> datetime:
    """SQLite gives timestamps back without a timezone; they are always UTC."""
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)
