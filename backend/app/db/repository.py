"""Every database query the service makes, in one place."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import BookingRecord


class BookingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, record: BookingRecord) -> BookingRecord:
        self._session.add(record)
        self._session.flush()
        return record

    def next_bill_number(self) -> int:
        """One past the highest bill number on record."""
        highest = self._session.scalar(select(func.max(BookingRecord.bill_number)))
        return (highest or 0) + 1

    def get(self, booking_id: str) -> BookingRecord | None:
        return self._session.get(BookingRecord, booking_id)

    def page(self, *, limit: int, offset: int) -> tuple[Sequence[BookingRecord], int]:
        """One page of bills, newest first, plus the unpaginated total.

        Ordered by bill number rather than by ``created_at``: it is the sequence
        the bills were actually issued in, and it is unique, so two bookings
        raised in the same millisecond still have one defined order.
        """
        total = self._session.scalar(select(func.count()).select_from(BookingRecord)) or 0
        statement = (
            select(BookingRecord)
            .order_by(BookingRecord.bill_number.desc())
            .limit(limit)
            .offset(offset)
        )
        return self._session.scalars(statement).all(), total
