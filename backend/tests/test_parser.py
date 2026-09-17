"""The parser's contract: what it reads, what it refuses, what it admits to guessing."""

from __future__ import annotations

import pytest

from app.domain.errors import RequestNotUnderstood, UnbookableRequest
from app.domain.models import GuestCountSource
from app.parsing.parser import parse

BRIEF_SAMPLE = (
    "Book 3 double rooms and 1 suite for 10 nights with half board "
    "for the lead cast and director"
)


def rooms_of(text: str) -> dict[str, int]:
    return {room.room_type: room.quantity for room in parse(text).rooms}


class TestTheBriefsSample:
    def test_reads_every_field(self) -> None:
        request = parse(BRIEF_SAMPLE)

        assert rooms_of(BRIEF_SAMPLE) == {"double": 3, "suite": 1}
        assert request.nights == 10
        assert request.meal_plan == "half_board"
        assert request.guests == 8
        assert request.guest_count_source is GuestCountSource.DERIVED_FROM_CAPACITY
        assert request.party == "the lead cast and director"
        assert request.warnings == ()


class TestRooms:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("2 single rooms for 3 nights", {"single": 2}),
            ("book 4 doubles for 3 nights", {"double": 4}),
            ("2 twin rooms for 3 nights", {"double": 2}),
            ("a suite for 3 nights", {"suite": 1}),
            ("three dorms for 3 nights", {"dormitory": 3}),
            ("2 dormitories for 3 nights", {"dormitory": 2}),
            ("book the bunkhouse for 3 nights", {"dormitory": 1}),
            ("2 flats for 3 nights", {"apartment": 2}),
            ("1 apt for 3 nights", {"apartment": 1}),
            ("a guest house for 3 nights", {"guesthouse": 1}),
            ("2 guesthouses for 3 nights", {"guesthouse": 2}),
        ],
    )
    def test_recognises_synonyms(self, text: str, expected: dict[str, int]) -> None:
        assert rooms_of(text) == expected

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("12 doubles for 2 nights", 12),
            ("twelve doubles for 2 nights", 12),
            ("twenty five doubles for 2 nights", 25),
            ("a couple of doubles for 2 nights", 2),
            ("2x doubles for 2 nights", 2),
            ("3 large doubles for 2 nights", 3),
        ],
    )
    def test_reads_counts_written_any_way(self, text: str, expected: int) -> None:
        assert rooms_of(text)["double"] == expected

    def test_sums_repeated_mentions_of_one_room_type(self) -> None:
        text = "2 doubles for the grips and 3 more doubles for the sparks, 4 nights"
        assert rooms_of(text) == {"double": 5}

    def test_keeps_the_order_the_request_named_them(self) -> None:
        request = parse("1 suite, 2 dorms and 3 doubles for 2 nights")
        assert [room.room_type for room in request.rooms] == [
            "suite",
            "dormitory",
            "double",
        ]

    @pytest.mark.parametrize(
        "text",
        [
            "a double room for a single night",
            "one apartment at the double occupancy rate for 4 nights",
            "an en suite double for 4 nights",
        ],
    )
    def test_ignores_room_words_doing_other_work(self, text: str) -> None:
        # "single" is a count here, "occupancy" and "en suite" are descriptions.
        assert "single" not in rooms_of(text)
        assert "suite" not in rooms_of(text)

    def test_warns_when_a_plural_has_no_count(self) -> None:
        request = parse("book doubles for 3 nights")

        assert request.rooms[0].quantity == 1
        assert any("No count given" in warning for warning in request.warnings)


class TestDuration:
    @pytest.mark.parametrize(
        ("text", "nights"),
        [
            ("a double for 10 nights", 10),
            ("a double for ten nights", 10),
            ("a double, 10-night stay", 10),
            ("a double for a week", 7),
            ("a double for 3 weeks", 21),
            ("a double for a fortnight", 14),
            ("a double overnight", 1),
            ("a double for the night", 1),
        ],
    )
    def test_reads_stay_length(self, text: str, nights: int) -> None:
        assert parse(text).nights == nights

    def test_reads_days_as_nights_but_says_so(self) -> None:
        request = parse("a double for 5 days")

        assert request.nights == 5
        assert any("'days' as nights" in warning for warning in request.warnings)

    def test_prefers_an_exact_unit_over_an_approximate_one(self) -> None:
        # "10 days" appears first, but "9 nights" is the unambiguous statement.
        assert parse("a double for 10 days, that is 9 nights").nights == 9

    def test_flags_contradictory_durations(self) -> None:
        request = parse("3 doubles for 10 nights plus a suite for 2 weeks")

        assert request.nights == 10
        assert any("more than one stay length" in w for w in request.warnings)

    def test_refuses_a_request_with_no_duration(self) -> None:
        with pytest.raises(RequestNotUnderstood) as raised:
            parse("book a suite for the director")

        assert raised.value.code == "no_duration_found"


class TestMealPlan:
    @pytest.mark.parametrize(
        ("text", "plan"),
        [
            ("a double for 2 nights with half board", "half_board"),
            ("a double for 2 nights, half-board", "half_board"),
            ("a double for 2 nights with breakfast and dinner", "half_board"),
            ("a double for 2 nights full board", "full_board"),
            ("a double for 2 nights, all meals included", "full_board"),
            ("a double for 2 nights with breakfast", "breakfast"),
            ("a double for 2 nights B&B", "breakfast"),
            ("a double for 2 nights, bed and breakfast", "breakfast"),
            ("a double for 2 nights, room only", "none"),
            ("a double for 2 nights, no meals", "none"),
            ("a double for 2 nights, self catering", "none"),
        ],
    )
    def test_recognises_how_meals_get_written(self, text: str, plan: str) -> None:
        assert parse(text).meal_plan == plan

    def test_a_refusal_beats_a_mention(self) -> None:
        assert parse("a double for 2 nights, no breakfast").meal_plan == "none"

    def test_defaults_to_room_only_but_says_so(self) -> None:
        request = parse("a double for 2 nights")

        assert request.meal_plan == "none"
        assert any("No meal plan mentioned" in w for w in request.warnings)


class TestGuests:
    @pytest.mark.parametrize(
        ("text", "guests"),
        [
            ("2 doubles for 2 nights for 3 people", 3),
            ("2 doubles for 2 nights for three guests", 3),
            ("2 doubles for 2 nights, party of 4", 4),
            ("2 doubles for 2 nights sleeping 4", 4),
            ("2 doubles for 2 nights for 4 crew", 4),
            ("a dormitory for 2 nights for a group of 6", 6),
        ],
    )
    def test_reads_a_stated_headcount(self, text: str, guests: int) -> None:
        request = parse(text)

        assert request.guests == guests
        assert request.guest_count_source is GuestCountSource.STATED

    def test_falls_back_to_the_capacity_booked(self) -> None:
        request = parse("2 doubles and a dormitory for 2 nights")

        assert request.guests == 2 * 2 + 8
        assert request.guest_count_source is GuestCountSource.DERIVED_FROM_CAPACITY

    def test_refuses_more_guests_than_beds(self) -> None:
        with pytest.raises(UnbookableRequest) as raised:
            parse("1 double for 2 nights for 6 people")

        assert raised.value.code == "insufficient_capacity"
        assert "sleep 2" in raised.value.message


class TestParty:
    @pytest.mark.parametrize(
        ("text", "party"),
        [
            ("a suite for 3 nights for the director", "the director"),
            ("2 doubles for 3 nights for the camera crew", "the camera crew"),
            ("a dorm for the stunt team for 3 nights", "the stunt team"),
            ("2 doubles for 3 nights for the grips please", "the grips"),
        ],
    )
    def test_captures_who_the_rooms_are_for(self, text: str, party: str) -> None:
        assert parse(text).party == party

    @pytest.mark.parametrize(
        "text",
        [
            "2 doubles for 10 nights",
            "2 doubles for 3 nights for 4 people",
            "2 doubles for three weeks",
        ],
    )
    def test_leaves_it_empty_when_for_introduces_a_quantity(self, text: str) -> None:
        assert parse(text).party is None


class TestRefusals:
    @pytest.mark.parametrize("text", ["", "   ", "\n"])
    def test_rejects_an_empty_request(self, text: str) -> None:
        with pytest.raises(RequestNotUnderstood) as raised:
            parse(text)

        assert raised.value.code == "empty_request"

    def test_rejects_a_request_with_no_room_type(self) -> None:
        with pytest.raises(RequestNotUnderstood) as raised:
            parse("somewhere to sleep for 4 nights")

        assert raised.value.code == "no_rooms_found"
        assert "dormitory" in (raised.value.hint or "")

    def test_rejects_an_implausible_stay(self) -> None:
        with pytest.raises(UnbookableRequest) as raised:
            parse("a double for 400 nights")

        assert raised.value.code == "stay_too_long"

    def test_rejects_an_implausible_room_count(self) -> None:
        with pytest.raises(UnbookableRequest) as raised:
            parse("500 doubles for 2 nights")

        assert raised.value.code == "too_many_rooms"

    def test_rejects_an_oversized_body(self) -> None:
        with pytest.raises(UnbookableRequest) as raised:
            parse("a double for 2 nights " + "x" * 3_000)

        assert raised.value.code == "request_too_long"


class TestDeterminism:
    def test_the_same_text_always_parses_the_same_way(self) -> None:
        assert parse(BRIEF_SAMPLE) == parse(BRIEF_SAMPLE)

    @pytest.mark.parametrize(
        "text",
        [
            BRIEF_SAMPLE,
            BRIEF_SAMPLE.upper(),
            "  book   3 DOUBLE rooms, and 1 Suite -- for 10 nights, with half-board, "
            "for the lead cast and director.  ",
        ],
    )
    def test_case_spacing_and_punctuation_do_not_change_the_reading(
        self, text: str
    ) -> None:
        request = parse(text)

        assert {room.room_type: room.quantity for room in request.rooms} == {
            "double": 3,
            "suite": 1,
        }
        assert request.nights == 10
        assert request.meal_plan == "half_board"
        assert request.guests == 8


class TestComposedRequests:
    """The UI's dropdown builder writes English and posts it like any other
    request, so there is one ingestion path and one set of rules. These are the
    exact sentence shapes it produces -- if the parser stops reading them, the
    builder is broken.
    """

    @pytest.mark.parametrize(
        ("text", "expected_rooms", "nights", "meal_plan"),
        [
            ("Book 1 suite for 1 night room only", {"suite": 1}, 1, "none"),
            (
                "Book 3 double rooms and 1 suite for 10 nights with half board",
                {"double": 3, "suite": 1},
                10,
                "half_board",
            ),
            (
                "Book 2 dormitories, 1 apartment and 4 single rooms "
                "for 12 nights with breakfast",
                {"dormitory": 2, "apartment": 1, "single": 4},
                12,
                "breakfast",
            ),
            (
                "Book 2 guesthouses for 5 nights with full board",
                {"guesthouse": 2},
                5,
                "full_board",
            ),
        ],
    )
    def test_reads_back_what_the_builder_wrote(
        self, text: str, expected_rooms: dict[str, int], nights: int, meal_plan: str
    ) -> None:
        request = parse(text)

        assert rooms_of(text) == expected_rooms
        assert request.nights == nights
        assert request.meal_plan == meal_plan

    def test_reads_back_an_optional_headcount_and_party(self) -> None:
        text = (
            "Book 3 double rooms and 1 suite for 10 nights with half board "
            "for 7 people for the lead cast and director"
        )

        request = parse(text)

        assert request.guests == 7
        assert request.guest_count_source is GuestCountSource.STATED
        assert request.party == "the lead cast and director"
