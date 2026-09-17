"""Cost a parsed :class:`BookingRequest`.

Rules, in the order the rate card applies them:

1. Rooms are charged at the nightly rate, per room, per night.
2. Meals are charged per guest, per night, at the meal plan's surcharge.
3. A stay longer than the extended-stay threshold takes a percentage off the
   combined room and meal subtotal.

Guests are seated room by room, in the order the request named them, filling
each room to capacity before moving on. That allocation only ever splits the
meal charge between lines -- the meal total is guests x rate x nights either
way -- so the per-room breakdown always adds up to the booking total.
"""

from __future__ import annotations

from decimal import Decimal

from app.domain.catalog import (
    CURRENCY,
    EXTENDED_STAY_DISCOUNT,
    MEAL_PLANS,
    ROOM_TYPES,
)
from app.domain.models import BookingRequest, Discount, Quote, RoomLine
from app.domain.money import ZERO, money

_HUNDRED = Decimal("100")


def quote(request: BookingRequest) -> Quote:
    """Price ``request`` against the rate card."""
    meal_plan = MEAL_PLANS[request.meal_plan]
    nights = Decimal(request.nights)

    lines: list[RoomLine] = []
    unseated = request.guests

    for selection in request.rooms:
        room = ROOM_TYPES[selection.room_type]
        seats = room.capacity * selection.quantity
        allocated = min(unseated, seats)
        unseated -= allocated

        room_charge = money(room.nightly_rate * nights * selection.quantity)
        meal_charge = money(meal_plan.surcharge * allocated * nights)

        lines.append(
            RoomLine(
                room_type=room.name,
                category=room.category,
                quantity=selection.quantity,
                nightly_rate=room.nightly_rate,
                capacity_per_room=room.capacity,
                nights=request.nights,
                room_charge=room_charge,
                guests_allocated=allocated,
                meal_rate_per_guest_night=meal_plan.surcharge,
                meal_charge=meal_charge,
                subtotal=room_charge + meal_charge,
            )
        )

    room_subtotal = sum((line.room_charge for line in lines), ZERO)
    meal_subtotal = sum((line.meal_charge for line in lines), ZERO)
    subtotal = room_subtotal + meal_subtotal

    qualifies = request.nights > EXTENDED_STAY_DISCOUNT.threshold
    discount_amount = (
        money(subtotal * EXTENDED_STAY_DISCOUNT.percent / _HUNDRED) if qualifies else ZERO
    )

    return Quote(
        currency=CURRENCY,
        nights=request.nights,
        guests=request.guests,
        meal_plan=request.meal_plan,
        lines=tuple(lines),
        room_subtotal=room_subtotal,
        meal_subtotal=meal_subtotal,
        subtotal=subtotal,
        discount=Discount(
            applied=qualifies,
            reason="extended_stay",
            threshold_nights=EXTENDED_STAY_DISCOUNT.threshold,
            percent=EXTENDED_STAY_DISCOUNT.percent,
            amount=discount_amount,
        ),
        total=subtotal - discount_amount,
    )
