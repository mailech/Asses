"""The rate card, applied. Every expected figure here is worked by hand."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.catalog import EXTENDED_STAY_DISCOUNT
from app.domain.money import money
from app.domain.pricing import quote
from app.parsing.parser import parse

BRIEF_SAMPLE = (
    "Book 3 double rooms and 1 suite for 10 nights with half board "
    "for the lead cast and director"
)


def price(text: str):
    return quote(parse(text))


#: A spread of shapes -- one room type and several, discounted and not, every
#: meal plan, guests stated and guests derived.
INTEGRITY_REQUESTS = [
    BRIEF_SAMPLE,
    "1 double for 7 nights",
    "3 dormitories for 9 nights full board for 20 people",
    "2 apartments, 1 guesthouse and 4 singles for 12 nights with breakfast",
    "1 suite for 1 night room only",
    "5 twins for 14 nights half board for 9 crew",
]


class TestTheBriefsSample:
    """3 doubles + 1 suite, 10 nights, half board, 8 guests.

    Rooms  3 x 120 x 10 = 3,600 and 1 x 250 x 10 = 2,500  ->  6,100
    Meals  35 x 8 guests x 10 nights                      ->  2,800
    Subtotal                                              ->  8,900
    Extended stay, 10 nights > 7, 15% of 8,900            -> -1,335
    Total                                                 ->  7,565
    """

    @pytest.fixture
    def result(self):
        return price(BRIEF_SAMPLE)

    def test_room_subtotal(self, result) -> None:
        assert result.room_subtotal == Decimal("6100.00")

    def test_meal_subtotal(self, result) -> None:
        assert result.meal_subtotal == Decimal("2800.00")

    def test_discount(self, result) -> None:
        assert result.discount.applied is True
        assert result.discount.amount == Decimal("1335.00")

    def test_total(self, result) -> None:
        assert result.total == Decimal("7565.00")

    def test_breakdown_per_room(self, result) -> None:
        doubles, suite = result.lines

        assert (doubles.quantity, doubles.guests_allocated) == (3, 6)
        assert doubles.room_charge == Decimal("3600.00")
        assert doubles.meal_charge == Decimal("2100.00")
        assert doubles.subtotal == Decimal("5700.00")

        assert (suite.quantity, suite.guests_allocated) == (1, 2)
        assert suite.room_charge == Decimal("2500.00")
        assert suite.meal_charge == Decimal("700.00")
        assert suite.subtotal == Decimal("3200.00")


class TestRoomCharges:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("1 single for 1 night", "80.00"),
            ("1 double for 1 night", "120.00"),
            ("1 suite for 1 night", "250.00"),
            ("1 dormitory for 1 night", "30.00"),
            ("1 apartment for 1 night", "200.00"),
            ("1 guesthouse for 1 night", "60.00"),
        ],
    )
    def test_one_room_for_one_night_is_the_nightly_rate(
        self, text: str, expected: str
    ) -> None:
        assert price(text).room_subtotal == Decimal(expected)

    def test_scales_with_rooms_and_nights(self) -> None:
        # 4 singles x 80 x 3 nights.
        assert price("4 singles for 3 nights").room_subtotal == Decimal("960.00")


class TestMealCharges:
    @pytest.mark.parametrize(
        ("plan", "expected"),
        [
            ("room only", "0.00"),
            ("with breakfast", "120.00"),   # 15 x 2 guests x 4 nights
            ("half board", "280.00"),       # 35 x 2 x 4
            ("full board", "480.00"),       # 60 x 2 x 4
        ],
    )
    def test_charged_per_guest_per_night(self, plan: str, expected: str) -> None:
        result = price(f"1 double for 4 nights {plan}")

        assert result.guests == 2
        assert result.meal_subtotal == Decimal(expected)

    def test_follows_the_guest_count_not_the_bed_count(self) -> None:
        # A dormitory sleeps 8, but only 3 people are eating.
        result = price("1 dormitory for 2 nights full board for 3 people")

        assert result.meal_subtotal == Decimal("360.00")  # 60 x 3 x 2

    def test_splits_guests_across_rooms_in_the_order_requested(self) -> None:
        # 5 guests: the apartment seats 4, the single takes the fifth.
        result = price("1 apartment and 1 single for 2 nights breakfast for 5 people")
        apartment, single = result.lines

        assert (apartment.guests_allocated, single.guests_allocated) == (4, 1)
        assert apartment.meal_charge == Decimal("120.00")  # 15 x 4 x 2
        assert single.meal_charge == Decimal("30.00")      # 15 x 1 x 2

    def test_a_room_with_nobody_in_it_is_charged_no_meals(self) -> None:
        # The apartment seats all 4; the guesthouse is still booked and still
        # billed for the room, but nobody eats in it.
        result = price(
            "1 apartment and 1 guesthouse for 2 nights full board for 4 people"
        )
        apartment, guesthouse = result.lines

        assert (apartment.guests_allocated, guesthouse.guests_allocated) == (4, 0)
        assert guesthouse.meal_charge == Decimal("0.00")
        assert guesthouse.room_charge == Decimal("120.00")


class TestExtendedStayDiscount:
    def test_does_not_apply_at_the_threshold(self) -> None:
        # The rule is "exceeds 7 nights", so 7 nights pays full price.
        result = price("1 double for 7 nights")

        assert result.nights == EXTENDED_STAY_DISCOUNT.threshold
        assert result.discount.applied is False
        assert result.discount.amount == Decimal("0.00")
        assert result.total == result.subtotal

    def test_applies_one_night_past_the_threshold(self) -> None:
        result = price("1 double for 8 nights")  # 960.00

        assert result.discount.applied is True
        assert result.discount.amount == Decimal("144.00")
        assert result.total == Decimal("816.00")

    def test_applies_to_rooms_and_meals_together(self) -> None:
        # 1 double, 10 nights, breakfast, 2 guests:
        # rooms 1,200 + meals 300 = 1,500; 15% of the whole 1,500 is 225.
        result = price("1 double for 10 nights with breakfast")

        assert result.subtotal == Decimal("1500.00")
        assert result.discount.amount == Decimal("225.00")
        assert result.total == Decimal("1275.00")

    def test_reports_the_rule_it_applied(self) -> None:
        discount = price("1 double for 8 nights").discount

        assert discount.reason == "extended_stay"
        assert discount.threshold_nights == 7
        assert discount.percent == Decimal("15")


class TestArithmeticIntegrity:
    @pytest.mark.parametrize("text", INTEGRITY_REQUESTS)
    def test_the_breakdown_adds_up_to_the_booking(self, text: str) -> None:
        result = price(text)

        assert sum(line.room_charge for line in result.lines) == result.room_subtotal
        assert sum(line.meal_charge for line in result.lines) == result.meal_subtotal
        assert sum(line.subtotal for line in result.lines) == result.subtotal
        assert result.subtotal - result.discount.amount == result.total

    @pytest.mark.parametrize("text", INTEGRITY_REQUESTS)
    def test_every_guest_is_seated_exactly_once(self, text: str) -> None:
        result = price(text)

        assert sum(line.guests_allocated for line in result.lines) == result.guests

    @pytest.mark.parametrize("text", INTEGRITY_REQUESTS)
    def test_every_amount_is_an_exact_number_of_cents(self, text: str) -> None:
        amounts = [
            result_amount
            for line in price(text).lines
            for result_amount in (line.room_charge, line.meal_charge, line.subtotal)
        ]
        amounts += [price(text).subtotal, price(text).total, price(text).discount.amount]

        for amount in amounts:
            assert isinstance(amount, Decimal)
            assert amount == amount.quantize(Decimal("0.01"))


class TestMoneyRounding:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [("2.674", "2.67"), ("2.675", "2.68"), ("2.665", "2.67"), ("0.005", "0.01")],
    )
    def test_rounds_half_up_the_way_an_invoice_does(
        self, raw: str, expected: str
    ) -> None:
        # Half-even would make 2.675 -> 2.68 but 2.665 -> 2.66; finance expects
        # both to round away from zero.
        assert money(Decimal(raw)) == Decimal(expected)
