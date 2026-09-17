"""Domain-level failures, kept free of any HTTP vocabulary."""

from __future__ import annotations


class BookingError(Exception):
    """Base class for anything the booking domain refuses to do."""

    code = "booking_error"

    def __init__(self, message: str, *, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint


class RequestNotUnderstood(BookingError):
    """The text was read, but a piece the booking cannot do without is missing."""

    def __init__(self, code: str, message: str, *, hint: str | None = None) -> None:
        super().__init__(message, hint=hint)
        self.code = code


class UnbookableRequest(BookingError):
    """The text was understood, but what it asks for cannot be booked."""

    def __init__(self, code: str, message: str, *, hint: str | None = None) -> None:
        super().__init__(message, hint=hint)
        self.code = code


class BookingNotFound(BookingError):
    code = "booking_not_found"

    def __init__(self, booking_id: str) -> None:
        super().__init__(f"No accommodation booking with id {booking_id!r}.")
        self.booking_id = booking_id
