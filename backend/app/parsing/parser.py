"""Read a plain-English lodging request into a :class:`BookingRequest`.

The strategy is a single normalisation pass followed by four independent
extractors -- rooms, duration, meal plan, guests -- each scanning the same token
list for the patterns it cares about. They are independent on purpose: a request
that phrases the duration oddly still gets its rooms read correctly, and a new
phrasing is supported by touching one extractor and the lexicon.

Anything an extractor had to assume is reported on ``BookingRequest.warnings``
rather than silently applied. A booking that quietly guessed its own length is
worse than one that says it guessed.
"""

from __future__ import annotations

from app.domain.catalog import (
    MAX_NIGHTS,
    MAX_ROOMS_PER_BOOKING,
    ROOM_TYPES,
    MealPlanName,
    RoomTypeName,
)
from app.domain.errors import RequestNotUnderstood, UnbookableRequest
from app.domain.models import BookingRequest, GuestCountSource, RoomSelection
from app.parsing.lexicon import (
    AMBIGUOUS_ROOM_ALIASES,
    DURATION_UNITS,
    GUEST_COLLECTIVES,
    GUEST_NOUNS,
    GUEST_VERBS,
    MAX_PARTY_TOKENS,
    MEAL_PLAN_PHRASES,
    NON_PARTY_WORDS,
    NON_ROOM_PREDECESSORS,
    NON_ROOM_SUCCESSORS,
    PARTY_TERMINATORS,
    POLITENESS,
    QUANTITY_FILLER,
    ROOM_ALIASES,
    ROOM_NOUNS,
    TENS,
    UNITS,
)
from app.parsing.normalize import tokenize

MAX_INPUT_CHARS = 2_000

_ROOM_TYPE_LIST = ", ".join(ROOM_TYPES)
#: How a person writes each plan, for messages a person will read.
_MEAL_PLAN_PHRASING = "'breakfast', 'half board' or 'full board'"


# --- Numbers ----------------------------------------------------------------


def _read_number_forward(tokens: list[str], index: int) -> tuple[int, int] | None:
    """Read a number starting at ``index``; return ``(value, index_after)``."""
    if not 0 <= index < len(tokens):
        return None
    token = tokens[index]
    if token.isdigit():
        return int(token), index + 1
    if token in TENS:
        following = tokens[index + 1] if index + 1 < len(tokens) else ""
        if 1 <= UNITS.get(following, 0) <= 9:
            return TENS[token] + UNITS[following], index + 2
        return TENS[token], index + 1
    if token in UNITS:
        return UNITS[token], index + 1
    return None


def _read_number_backward(tokens: list[str], index: int) -> int | None:
    """Read a number ending at ``index`` ("twenty five" -> 25)."""
    if not 0 <= index < len(tokens):
        return None
    token = tokens[index]
    if token.isdigit():
        return int(token)
    if token in UNITS:
        value = UNITS[token]
        previous = tokens[index - 1] if index >= 1 else ""
        if 1 <= value <= 9 and previous in TENS:
            return TENS[previous] + value
        return value
    if token in TENS:
        return TENS[token]
    return None


def _quantity_before(tokens: list[str], index: int) -> int | None:
    """The count attached to the noun at ``index``, skipping any adjectives."""
    cursor = index - 1
    while cursor >= 0 and tokens[cursor] in QUANTITY_FILLER:
        cursor -= 1
    return _read_number_backward(tokens, cursor)


# --- Rooms ------------------------------------------------------------------


def _match_room_alias(tokens: list[str], index: int) -> tuple[RoomTypeName, int] | None:
    """Longest-first alias match at ``index``; returns the type and its length."""
    for length in (2, 1):
        if index + length > len(tokens):
            continue
        room_type = ROOM_ALIASES.get(tuple(tokens[index : index + length]))
        if room_type is not None:
            return room_type, length
    return None


def _extract_rooms(tokens: list[str]) -> tuple[list[RoomSelection], list[str]]:
    counts: dict[RoomTypeName, int] = {}
    warnings: list[str] = []
    index = 0

    while index < len(tokens):
        match = _match_room_alias(tokens, index)
        if match is None:
            index += 1
            continue

        room_type, length = match
        end = index + length
        alias = tokens[index:end]
        following = tokens[end] if end < len(tokens) else ""

        # "an en suite double" names a feature, not a suite.
        if index > 0 and tokens[index - 1] in NON_ROOM_PREDECESSORS:
            index = end
            continue
        # "a single night", "double occupancy" -- the alias is doing other work.
        if alias[0] in AMBIGUOUS_ROOM_ALIASES and following in NON_ROOM_SUCCESSORS:
            index = end
            continue

        quantity = _quantity_before(tokens, index)
        if quantity is None:
            quantity = 1
            if alias[-1].endswith("s"):
                plural = " ".join(alias)
                warnings.append(f"No count given for {plural!r}; booked 1.")
        if quantity < 1:
            index = end
            continue

        counts[room_type] = counts.get(room_type, 0) + quantity
        # Swallow a trailing "rooms" so it cannot start another match.
        index = end + 1 if following in ROOM_NOUNS else end

    selections = [RoomSelection(name, count) for name, count in counts.items()]
    return selections, warnings


# --- Duration ---------------------------------------------------------------


def _extract_nights(tokens: list[str]) -> tuple[int | None, list[str]]:
    warnings: list[str] = []
    exact: list[tuple[int, int]] = []          # (position, nights)
    approximate: list[tuple[int, int, str]] = []  # (position, nights, unit read)

    for index, token in enumerate(tokens):
        if token == "overnight":
            exact.append((index, 1))
            continue
        unit = DURATION_UNITS.get(token)
        if unit is None:
            continue
        nights_per_unit, is_exact = unit
        count = _quantity_before(tokens, index)
        if count is None:
            if token.endswith("s"):
                continue  # "for nights" states no length at all.
            count = 1
        if count < 1:
            continue
        total = count * nights_per_unit
        if is_exact:
            exact.append((index, total))
        else:
            approximate.append((index, total, token))

    if exact:
        distinct = sorted({nights for _, nights in exact})
        if len(distinct) > 1:
            lengths = ", ".join(f"{nights} nights" for nights in distinct)
            warnings.append(
                f"Request mentions more than one stay length ({lengths}); used the first."
            )
        return exact[0][1], warnings

    if approximate:
        _, nights, unit = approximate[0]
        warnings.append(f"Read {unit!r} as nights; booked {nights} nights.")
        return nights, warnings

    return None, warnings


# --- Meal plan --------------------------------------------------------------


def _extract_meal_plan(tokens: list[str]) -> tuple[MealPlanName, bool]:
    """The meal plan and whether the request actually named one."""
    for phrase, plan in MEAL_PLAN_PHRASES:
        span = len(phrase)
        for index in range(len(tokens) - span + 1):
            if tuple(tokens[index : index + span]) == phrase:
                return plan, True
    return "none", False


# --- Guests -----------------------------------------------------------------


def _extract_guests(tokens: list[str]) -> int | None:
    # "party of 8", "group of twelve"
    for index, token in enumerate(tokens):
        if token in GUEST_COLLECTIVES and tokens[index + 1 : index + 2] == ["of"]:
            number = _read_number_forward(tokens, index + 2)
            if number is not None and number[0] > 0:
                return number[0]

    # "sleeping 6", "accommodating twelve"
    for index, token in enumerate(tokens):
        if token in GUEST_VERBS:
            number = _read_number_forward(tokens, index + 1)
            if number is not None and number[0] > 0:
                return number[0]

    # "6 people", "twelve crew"
    for index, token in enumerate(tokens):
        if token in GUEST_NOUNS:
            count = _quantity_before(tokens, index)
            if count is not None and count > 0:
                return count

    return None


# --- Party ------------------------------------------------------------------


def _extract_party(tokens: list[str]) -> str | None:
    """The trailing "for ..." clause that names people rather than a quantity."""
    candidate: str | None = None

    for index, token in enumerate(tokens):
        if token != "for":
            continue
        phrase: list[str] = []
        for word in tokens[index + 1 : index + 1 + MAX_PARTY_TOKENS]:
            if word in PARTY_TERMINATORS:
                break
            phrase.append(word)
        while phrase and phrase[-1] in POLITENESS:
            phrase.pop()
        if not phrase or any(word.isdigit() for word in phrase):
            continue
        if all(word in NON_PARTY_WORDS for word in phrase):
            continue
        candidate = " ".join(phrase)

    return candidate


# --- Entry point ------------------------------------------------------------


def parse(text: str) -> BookingRequest:
    """Parse ``text`` into a validated :class:`BookingRequest`.

    Raises:
        RequestNotUnderstood: a detail the booking cannot do without is missing.
        UnbookableRequest: the request is clear but cannot be fulfilled.
    """
    if not text or not text.strip():
        raise RequestNotUnderstood(
            "empty_request",
            "The accommodation request is empty.",
            hint='Try: "Book 3 double rooms for 10 nights with half board".',
        )
    if len(text) > MAX_INPUT_CHARS:
        raise UnbookableRequest(
            "request_too_long",
            f"The request is {len(text)} characters; the limit is {MAX_INPUT_CHARS}.",
            hint="Split multi-department requests into one booking each.",
        )

    tokens = tokenize(text)
    warnings: list[str] = []

    rooms, room_warnings = _extract_rooms(tokens)
    warnings.extend(room_warnings)
    if not rooms:
        raise RequestNotUnderstood(
            "no_rooms_found",
            "No recognisable room type was found in the request.",
            hint=f"Supported room types: {_ROOM_TYPE_LIST}.",
        )

    total_rooms = sum(room.quantity for room in rooms)
    if total_rooms > MAX_ROOMS_PER_BOOKING:
        raise UnbookableRequest(
            "too_many_rooms",
            f"{total_rooms} rooms exceeds the {MAX_ROOMS_PER_BOOKING}-room limit "
            "for a single booking.",
            hint="Raise separate bookings per location or department.",
        )

    nights, night_warnings = _extract_nights(tokens)
    warnings.extend(night_warnings)
    if nights is None:
        raise RequestNotUnderstood(
            "no_duration_found",
            "The length of the stay was not stated.",
            hint='Add a duration, for example "for 10 nights" or "for 2 weeks".',
        )
    if nights > MAX_NIGHTS:
        raise UnbookableRequest(
            "stay_too_long",
            f"A {nights}-night stay exceeds the {MAX_NIGHTS}-night limit.",
            hint="Long-lease accommodation is arranged outside this system.",
        )

    meal_plan, meal_plan_stated = _extract_meal_plan(tokens)
    if not meal_plan_stated:
        warnings.append(
            "No meal plan mentioned; booked room only. "
            f"Add {_MEAL_PLAN_PHRASING} to include meals."
        )

    capacity = sum(
        ROOM_TYPES[room.room_type].capacity * room.quantity for room in rooms
    )
    stated_guests = _extract_guests(tokens)
    if stated_guests is None:
        guests = capacity
        guest_count_source = GuestCountSource.DERIVED_FROM_CAPACITY
    else:
        guests = stated_guests
        guest_count_source = GuestCountSource.STATED

    if guests > capacity:
        raise UnbookableRequest(
            "insufficient_capacity",
            f"{guests} guests were requested but the rooms booked sleep {capacity}.",
            hint="Add rooms, or reduce the guest count to fit the rooms booked.",
        )

    return BookingRequest(
        rooms=tuple(rooms),
        nights=nights,
        meal_plan=meal_plan,
        guests=guests,
        guest_count_source=guest_count_source,
        party=_extract_party(tokens),
        warnings=tuple(warnings),
    )
