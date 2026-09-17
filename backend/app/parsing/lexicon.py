"""The vocabulary the parser recognises.

Everything the production office is likely to write lives here as data, so
teaching the parser a new phrase is a one-line change with a matching test
rather than a new branch in the parsing code.

Phrases are stored as token tuples because the parser works on tokens, not on
the raw string: that way "half-board", "half board" and "half  board" are the
same key by the time they reach a lookup.
"""

from __future__ import annotations

from typing import Final

from app.domain.catalog import MealPlanName, RoomTypeName

Phrase = tuple[str, ...]


def _phrases(mapping: dict[str, str]) -> dict[Phrase, str]:
    return {tuple(alias.split()): value for alias, value in mapping.items()}


# --- Numbers ----------------------------------------------------------------

UNITS: Final[dict[str, int]] = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    # Quantities people write instead of a digit.
    "a": 1, "an": 1, "single": 1, "couple": 2, "pair": 2, "dozen": 12,
}

TENS: Final[dict[str, int]] = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

#: Words that may sit between a quantity and the noun it counts.
QUANTITY_FILLER: Final[frozenset[str]] = frozenset(
    {
        "of", "more", "extra", "additional", "further", "spare", "other",
        "large", "small", "big", "standard", "premium", "budget", "basic",
        "shared", "private", "good", "nice", "quiet",
    }
)


# --- Rooms ------------------------------------------------------------------

ROOM_ALIASES: Final[dict[Phrase, RoomTypeName]] = _phrases(
    {
        "single": "single",
        "singles": "single",
        "single room": "single",
        "single rooms": "single",
        "solo room": "single",
        "solo rooms": "single",
        "double": "double",
        "doubles": "double",
        "double room": "double",
        "double rooms": "double",
        "twin": "double",
        "twins": "double",
        "twin room": "double",
        "twin rooms": "double",
        "suite": "suite",
        "suites": "suite",
        "dormitory": "dormitory",
        "dormitories": "dormitory",
        "dorm": "dormitory",
        "dorms": "dormitory",
        "dorm room": "dormitory",
        "dorm rooms": "dormitory",
        "bunkhouse": "dormitory",
        "bunk room": "dormitory",
        "bunk rooms": "dormitory",
        "apartment": "apartment",
        "apartments": "apartment",
        "apt": "apartment",
        "apts": "apartment",
        "flat": "apartment",
        "flats": "apartment",
        "guesthouse": "guesthouse",
        "guesthouses": "guesthouse",
        "guest house": "guesthouse",
        "guest houses": "guesthouse",
    }
)

#: Aliases that double as ordinary English ("a single night"). When one of these
#: is followed by a word in ``NON_ROOM_SUCCESSORS`` it is not a room at all.
AMBIGUOUS_ROOM_ALIASES: Final[frozenset[str]] = frozenset(
    {"single", "double", "twin", "flat"}
)

#: "an en suite double" -- the word after these is describing, not naming.
NON_ROOM_PREDECESSORS: Final[frozenset[str]] = frozenset({"en", "ensuite"})

NON_ROOM_SUCCESSORS: Final[frozenset[str]] = frozenset(
    {
        "night", "nights", "day", "days", "week", "weeks", "month", "months",
        "occupancy", "bed", "beds", "rate", "rates", "supplement", "use",
    }
)

#: Consumed after a room alias so "3 double rooms" does not leave "rooms" behind.
ROOM_NOUNS: Final[frozenset[str]] = frozenset({"room", "rooms", "unit", "units"})


# --- Duration ---------------------------------------------------------------

#: Duration noun -> nights per unit. ``exact`` marks the units we can take at
#: face value; the others are approximations worth telling the caller about.
DURATION_UNITS: Final[dict[str, tuple[int, bool]]] = {
    "night": (1, True),
    "nights": (1, True),
    "nite": (1, True),
    "nites": (1, True),
    "week": (7, True),
    "weeks": (7, True),
    "fortnight": (14, True),
    "fortnights": (14, True),
    "day": (1, False),
    "days": (1, False),
    "month": (30, False),
    "months": (30, False),
}

STANDALONE_DURATIONS: Final[dict[Phrase, int]] = _phrases(
    {"overnight": 1, "fortnight": 14, "a fortnight": 14}
)


# --- Meal plans -------------------------------------------------------------

#: Checked in order: the first hit wins, so the most specific phrases come first.
MEAL_PLAN_PHRASES: Final[tuple[tuple[Phrase, MealPlanName], ...]] = tuple(
    (tuple(alias.split()), plan)
    for alias, plan in [
        # Explicit refusals.
        ("no meals", "none"),
        ("no meal", "none"),
        ("no food", "none"),
        ("no board", "none"),
        ("no catering", "none"),
        ("no breakfast", "none"),
        ("without meals", "none"),
        ("room only", "none"),
        ("rooms only", "none"),
        ("self catering", "none"),
        ("self catered", "none"),
        ("meals not included", "none"),
        # Full board.
        ("full board", "full_board"),
        ("full boarding", "full_board"),
        ("full pension", "full_board"),
        ("all meals", "full_board"),
        ("all inclusive", "full_board"),
        ("fully catered", "full_board"),
        ("three meals", "full_board"),
        ("3 meals", "full_board"),
        ("breakfast lunch and dinner", "full_board"),
        # Half board.
        ("half board", "half_board"),
        ("half boarding", "half_board"),
        ("half pension", "half_board"),
        ("breakfast and dinner", "half_board"),
        ("dinner and breakfast", "half_board"),
        ("breakfast and evening meal", "half_board"),
        ("two meals", "half_board"),
        ("2 meals", "half_board"),
        # Breakfast only.
        ("bed and breakfast", "breakfast"),
        ("b and b", "breakfast"),
        ("bnb", "breakfast"),
        ("continental breakfast", "breakfast"),
        ("breakfast only", "breakfast"),
        ("breakfast included", "breakfast"),
        ("with breakfast", "breakfast"),
        ("breakfast", "breakfast"),
    ]
)


# --- Guests -----------------------------------------------------------------

GUEST_NOUNS: Final[frozenset[str]] = frozenset(
    {
        "person", "people", "persons", "guest", "guests", "adult", "adults",
        "pax", "head", "heads", "crew", "cast", "staff", "members", "member",
        "attendees", "occupants", "bodies",
    }
)

#: "party of 8", "group of twelve" -- the count comes after the noun.
GUEST_COLLECTIVES: Final[frozenset[str]] = frozenset(
    {"party", "group", "team", "unit", "crew", "cohort"}
)

GUEST_VERBS: Final[frozenset[str]] = frozenset(
    {"sleeps", "sleeping", "accommodating", "housing"}
)


# --- Party / occupant description -------------------------------------------

#: A "for ..." phrase ends when one of these starts a new clause.
PARTY_STOP_WORDS: Final[frozenset[str]] = frozenset(
    {
        "with", "for", "from", "at", "on", "in", "starting", "beginning",
        "between", "arriving", "departing", "checking", "plus", "including",
        "under", "during",
    }
)

POLITENESS: Final[frozenset[str]] = frozenset(
    {"please", "thanks", "thank", "you", "asap", "urgently"}
)

#: A "for ..." phrase made only of these is about the booking, not the people.
NON_PARTY_WORDS: Final[frozenset[str]] = (
    frozenset(DURATION_UNITS)
    | ROOM_NOUNS
    | GUEST_NOUNS
    | {"the", "a", "an", "our", "their", "his", "her", "its", "now", "then"}
)

NUMBER_WORDS: Final[frozenset[str]] = frozenset(UNITS) | frozenset(TENS)

#: A "for ..." phrase also ends as soon as it runs into a quantity, a duration,
#: a room or a meal plan -- those belong to the booking, not to the people.
PARTY_TERMINATORS: Final[frozenset[str]] = (
    PARTY_STOP_WORDS
    | NUMBER_WORDS
    | frozenset(DURATION_UNITS)
    | ROOM_NOUNS
    | frozenset(phrase[0] for phrase in ROOM_ALIASES)
    | frozenset(phrase[0] for phrase, _ in MEAL_PLAN_PHRASES)
    | {"overnight"}
)

#: Long enough for "the second unit camera department", short enough that a
#: rambling email body never ends up in the field.
MAX_PARTY_TOKENS: Final = 12
