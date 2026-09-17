"""The rate card the production office works from.

These three tables are the only source of truth for pricing. They are given by
the business, not derived, so they live apart from the logic that consumes them.
Rates are ``Decimal`` because every downstream calculation is money.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Final, Literal, NamedTuple

RoomCategory = Literal["budget", "standard", "premium"]
RoomTypeName = Literal[
    "single", "double", "suite", "dormitory", "apartment", "guesthouse"
]
MealPlanName = Literal["none", "breakfast", "half_board", "full_board"]


class RoomType(NamedTuple):
    name: RoomTypeName
    nightly_rate: Decimal
    capacity: int
    category: RoomCategory


class MealPlan(NamedTuple):
    name: MealPlanName
    #: Charged per guest, per night.
    surcharge: Decimal


class ExtendedStayDiscount(NamedTuple):
    #: Nights must *exceed* this value for the discount to apply.
    threshold: int
    percent: Decimal


ROOM_TYPES: Final[dict[RoomTypeName, RoomType]] = {
    "single": RoomType("single", Decimal("80.00"), 1, "standard"),
    "double": RoomType("double", Decimal("120.00"), 2, "standard"),
    "suite": RoomType("suite", Decimal("250.00"), 2, "premium"),
    "dormitory": RoomType("dormitory", Decimal("30.00"), 8, "budget"),
    "apartment": RoomType("apartment", Decimal("200.00"), 4, "premium"),
    "guesthouse": RoomType("guesthouse", Decimal("60.00"), 3, "standard"),
}

MEAL_PLANS: Final[dict[MealPlanName, MealPlan]] = {
    "none": MealPlan("none", Decimal("0.00")),
    "breakfast": MealPlan("breakfast", Decimal("15.00")),
    "half_board": MealPlan("half_board", Decimal("35.00")),
    "full_board": MealPlan("full_board", Decimal("60.00")),
}

EXTENDED_STAY_DISCOUNT: Final = ExtendedStayDiscount(
    threshold=7, percent=Decimal("15")
)

CURRENCY: Final = "INR"

#: Longest sensible booking the office will accept without a manual override.
MAX_NIGHTS: Final = 365
#: Guard against a fat-fingered "300 suites" emptying the budget by accident.
MAX_ROOMS_PER_BOOKING: Final = 200
