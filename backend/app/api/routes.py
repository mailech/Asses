"""The accommodation endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.errors import HTTP_422_UNPROCESSABLE, InvalidPayload
from app.db.session import get_session
from app.schemas import (
    AccommodationRequest,
    BookingOut,
    BookingPageOut,
    ErrorOut,
)
from app.services import bookings as service

router = APIRouter(prefix="/accommodations", tags=["accommodations"])

SessionDep = Annotated[Session, Depends(get_session)]

_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    status.HTTP_400_BAD_REQUEST: {"model": ErrorOut, "description": "Malformed body"},
    HTTP_422_UNPROCESSABLE: {
        "model": ErrorOut,
        "description": "The request could not be read, or cannot be booked",
    },
}

_REQUEST_BODY_SPEC = {
    "required": True,
    "content": {
        "application/json": {
            "schema": {"$ref": "#/components/schemas/AccommodationRequest"}
        },
        "text/plain": {"schema": {"type": "string"}},
    },
}


async def accommodation_text(request: Request) -> str:
    """The lodging request body, sent either as JSON or as plain text.

    ``{"text": "..."}`` is the documented contract; ``text/plain`` is accepted
    too, because half the callers of an endpoint like this are a curl one-liner
    pasted out of a production office email.
    """
    body = await request.body()
    if not body.strip():
        raise InvalidPayload("The request body is empty.")

    media_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if media_type in {"text/plain", ""}:
        return body.decode("utf-8", errors="replace")

    if media_type != "application/json":
        raise InvalidPayload(
            f"Unsupported content type {media_type!r}.",
            hint="Send application/json or text/plain.",
        )

    try:
        return AccommodationRequest.model_validate_json(body).text
    except ValidationError as exc:
        detail = exc.errors()[0]
        field = ".".join(str(part) for part in detail["loc"]) or "body"
        raise InvalidPayload(f"{field}: {detail['msg']}.") from exc


@router.post(
    "",
    response_model=BookingOut,
    status_code=status.HTTP_201_CREATED,
    summary="Book accommodation from a plain-English request",
    responses=_ERROR_RESPONSES,
    openapi_extra={"requestBody": _REQUEST_BODY_SPEC},
)
def create_accommodation(
    session: SessionDep,
    text: Annotated[str, Depends(accommodation_text)],
) -> BookingOut:
    """Parse the request, cost it against the rate card, and store the booking."""
    return service.create_booking(session, text)


@router.get(
    "",
    response_model=BookingPageOut,
    summary="List accommodation bookings, newest first",
)
def list_accommodations(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=service.MAX_PAGE_SIZE)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> BookingPageOut:
    return service.list_bookings(session, limit=limit, offset=offset)


@router.get(
    "/{booking_id}",
    response_model=BookingOut,
    summary="Retrieve one accommodation booking",
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorOut, "description": "Unknown booking"}
    },
)
def get_accommodation(
    session: SessionDep,
    booking_id: Annotated[str, Path(min_length=1, max_length=36)],
) -> BookingOut:
    return service.get_booking(session, booking_id)
