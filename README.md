# Accommodation Manager

A backend service that reads a crew lodging request written in plain English,
costs it against the production's rate card, and keeps the booking on record.
A small Next.js front end sits on top of it.

```
"Book 3 double rooms and 1 suite for 10 nights with half board
 for the lead cast and director"

  ->  3 doubles + 1 suite, 10 nights, half board, 8 guests
  ->  lodging 6,100.00 + meals 2,800.00 - extended stay 1,335.00
  ->  $7,565.00
```

Parsing and costing are rule-based. No model is called at any point, the same
text always produces the same booking, and every figure on a quote traces back
to a line in the rate card.

---

## Running it locally

Two terminals. Nothing to install beyond Python 3.11+ and Node 20+ — the default
database is a SQLite file, so there is no infrastructure to stand up first.

### 1. The API

```bash
cd backend
python -m venv .venv

.venv\Scripts\activate            # Windows (PowerShell or cmd)
source .venv/bin/activate         # macOS / Linux

pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

- API: <http://127.0.0.1:8000>
- Interactive docs: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/health>

A `accommodation.db` file appears in `backend/` on first start. Run only the
activate line for your platform.

### 2. The web UI

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:3000>. The UI talks to its own `/api` routes, which
forward to the API; set `API_BASE_URL` if the backend is not on port 8000.

### 3. The tests

```bash
cd backend
pytest              # 162 tests
ruff check app tests
```

---

## The API

Three endpoints, as specified, plus a health check.

### `POST /accommodations`

Accepts `{"text": "..."}` as JSON, or the request as a `text/plain` body.

```bash
curl -X POST http://127.0.0.1:8000/accommodations \
  -H "Content-Type: application/json" \
  -d '{"text":"Book 3 double rooms and 1 suite for 10 nights with half board for the lead cast and director"}'
```

```json
{
  "booking_id": "4ee74a7f-78d1-4bfd-ab04-ec46421d4ecb",
  "created_at": "2026-09-17T12:35:04.182Z",
  "raw_input": "Book 3 double rooms and 1 suite for 10 nights with half board for the lead cast and director",
  "request": {
    "rooms": [
      { "room_type": "double", "quantity": 3 },
      { "room_type": "suite", "quantity": 1 }
    ],
    "nights": 10,
    "meal_plan": "half_board",
    "guests": 8,
    "guest_count_source": "derived_from_capacity",
    "party": "the lead cast and director",
    "warnings": []
  },
  "quote": {
    "currency": "INR",
    "nights": 10,
    "guests": 8,
    "meal_plan": "half_board",
    "rooms": [
      {
        "room_type": "double",
        "category": "standard",
        "quantity": 3,
        "capacity_per_room": 2,
        "nightly_rate": "120.00",
        "nights": 10,
        "room_charge": "3600.00",
        "guests_allocated": 6,
        "meal_rate_per_guest_night": "35.00",
        "meal_charge": "2100.00",
        "subtotal": "5700.00"
      },
      {
        "room_type": "suite",
        "category": "premium",
        "quantity": 1,
        "capacity_per_room": 2,
        "nightly_rate": "250.00",
        "nights": 10,
        "room_charge": "2500.00",
        "guests_allocated": 2,
        "meal_rate_per_guest_night": "35.00",
        "meal_charge": "700.00",
        "subtotal": "3200.00"
      }
    ],
    "room_subtotal": "6100.00",
    "meal_subtotal": "2800.00",
    "subtotal": "8900.00",
    "discount": {
      "applied": true,
      "reason": "extended_stay",
      "threshold_nights": 7,
      "percent": "15",
      "amount": "1335.00"
    },
    "total": "7565.00"
  }
}
```

Each booking is issued a sequential bill reference — `ACM-2026-00001` — allocated
under a unique constraint, so two concurrent writers cannot share one. The loser
of a race retries rather than issuing a duplicate.

### `GET /accommodations/{booking_id}`

Returns the booking exactly as it was confirmed — the stored document, not a
re-computation. If the rate card changes next month, an existing booking still
reads back at the price it was agreed at.

### `GET /accommodations?limit=20&offset=0`

A page of summaries, newest first, with the unpaginated `count` alongside.

### Errors

Every failure uses one envelope. `code` is stable and machine-readable, `message`
says what happened, `hint` says what to do about it.

```json
{
  "error": {
    "code": "insufficient_capacity",
    "message": "6 guests were requested but the rooms booked sleep 2.",
    "hint": "Add rooms, or reduce the guest count to fit the rooms booked."
  }
}
```

| Status | When |
| --- | --- |
| `400 invalid_payload` | The body itself is wrong — empty, not JSON, missing `text`. |
| `404 booking_not_found` | No booking with that id. |
| `422 no_rooms_found` | No recognisable room type in the text. |
| `422 no_duration_found` | The text never says how long the stay is. |
| `422 insufficient_capacity` | More guests than the requested rooms sleep. |
| `422 too_many_rooms` / `stay_too_long` | Beyond the per-booking sanity limits. |

Every response carries an `X-Request-ID`, echoed from the request if one was
supplied, and every log line for that request is tagged with it.

---

## How the text is read

One normalisation pass, then four independent extractors over the same token
list. They are independent on purpose: a request that phrases its duration oddly
still gets its rooms read correctly. The vocabulary each one recognises lives as
data in `app/parsing/lexicon.py`, so teaching the parser a new phrase is a
one-line change plus a test.

| | Recognises | Examples |
| --- | --- | --- |
| **Rooms** | All six types plus common aliases and counts written as digits, words, or `2x` | `3 double rooms`, `a couple of twins`, `twenty five dorms`, `2 flats`, `the bunkhouse` |
| **Duration** | Nights, weeks, fortnights, and days (with a warning) | `for 10 nights`, `10-night stay`, `for a week`, `a fortnight`, `overnight` |
| **Meals** | Every plan, plus refusals | `half board`, `B&B`, `bed and breakfast`, `all meals`, `room only`, `self catering`, `no meals` |
| **Guests** | Stated headcounts in several forms | `for 6 people`, `party of 8`, `sleeping 4`, `a group of twelve` |
| **Party** | Who the rooms are for | `for the lead cast and director`, `for the stunt team` |

It also declines to be fooled by room words doing other work: `a single night` is
a duration, `double occupancy` is a rate description, and `an en suite double` is
one double room.

**Anything assumed is reported, never applied silently.** `warnings` on the
response is where the parser admits what it had to guess:

```
"Read 'days' as nights; booked 5 nights."
"No count given for 'doubles'; booked 1."
"Request mentions more than one stay length (10 nights, 14 nights); used the first."
"No meal plan mentioned; booked room only. Add 'breakfast', 'half board' or 'full board' to include meals."
```

Where a detail is missing rather than ambiguous — no room type, no duration —
the request is refused. A booking system that invents a duration is worse than
one that asks.

---

## How a booking is costed

```
room_charge   = nightly_rate x nights x quantity
meal_charge   = meal_surcharge x guests_in_those_rooms x nights
subtotal      = sum of both, across every room type
discount      = 15% of the subtotal, when nights > 7
total         = subtotal - discount
```

The brief left four things open. Each was decided once, written down here, and
pinned by a test.

**"Exceeds 7 nights" means strictly more than seven.** A 7-night stay pays full
price; 8 nights takes the discount. (`test_pricing.py::TestExtendedStayDiscount`)

**The discount applies to rooms and meals together.** The requirements read as a
pipeline — rooms, then meals, then the discount — so the discount comes off the
combined subtotal rather than lodging alone.

**An unstated guest count means full occupancy.** The sample request names no
headcount, so 3 doubles and a suite are taken as 8 guests. The response says
which it was via `guest_count_source`, so a caller is never guessing.

**Meals follow guests, not beds.** A dormitory sleeps 8, but if 3 people are
staying in it, 3 people eat. Guests are seated room type by room type in the
order the request named them, filling each to capacity; that only ever splits the
meal charge between lines, so the breakdown always sums to the total.

More guests than beds is refused rather than quietly adjusted — it is a real
booking error, and the office needs to see it.

### Money

Every amount is a `Decimal` from end to end, rounded to cents half-away-from-zero
the way an invoice is. Amounts cross the wire as **strings** (`"7565.00"`),
because JSON numbers are IEEE doubles and a booking total is not something to
hand to a format that cannot represent 0.1. In the database the sortable total is
stored as integer cents; the authoritative record is the JSON quote.

---

## Persistence

Both halves of the requirement sit on one row: `raw_input` is exactly what the
production office typed, and `parsed_request` / `quote` are the structured output
returned for it.

| Column | Purpose |
| --- | --- |
| `id`, `created_at` | Identity and ordering |
| `raw_input` | The request, verbatim |
| `parsed_request`, `quote` | The structured output, as JSON (JSONB on PostgreSQL) |
| `currency`, `total_cents`, `nights`, `guests`, `room_count`, `meal_plan` | Denormalised so the list endpoint never opens a JSON document |

The default is SQLite so a fresh checkout runs with no setup. PostgreSQL is one
environment variable away, and that is what this was last run against — a hosted
Neon instance, with the schema created by `alembic upgrade head`:

```bash
# backend/.env
DATABASE_URL=postgresql+psycopg://user:password@host.neon.tech/neondb?sslmode=require
AUTO_CREATE_SCHEMA=false
```

`docker-compose.yml` brings up a local PostgreSQL and the API together as an
alternative. That path is configured but was not exercised while building this —
the Docker daemon was unavailable on the machine it was written on. Everything
else described here was run against both SQLite and PostgreSQL.

Credentials live in `backend/.env`, which is git-ignored and excluded from the
submission archive.

### Schema management

Alembic owns the schema. `AUTO_CREATE_SCHEMA=true` (the default) creates tables
on startup so local development needs no extra step; turn it off wherever
migrations run:

```bash
cd backend
alembic upgrade head
```

The two definitions cannot drift: `tests/test_migrations.py` runs the migrations
against an empty database and compares the result to the ORM metadata, column by
column.

---

## Tests

162 tests, about half a second.

| File | Covers |
| --- | --- |
| `test_parser.py` | 75 cases: every room alias, every way a count or duration gets written, every meal-plan phrasing, the ambiguity guards, the warnings, and each refusal |
| `test_pricing.py` | The brief's worked example figure by figure, each rate in isolation, the discount boundary at 7 and 8 nights, guest seating, and an integrity check that every breakdown adds up to its total |
| `test_api.py` | The HTTP contract against a real app and a real database: status codes, the exact response shape, plain-text bodies, pagination, ordering, the error envelope, and that a rejected request writes nothing |
| `test_migrations.py` | Migrations and models describe the same schema; downgrade removes what upgrade created |
| `test_observability.py` | The id on the response is the id in the log, and an upstream one survives the hop |

The expected figures in `test_pricing.py` are worked by hand in the docstrings,
not copied from the implementation's output.

---

## Layout

```
backend/
  app/
    domain/          catalog (the rate card), models, pricing, money, errors
    parsing/         lexicon (vocabulary as data), normalize, parser
    db/              ORM models, session, repository
    services/        the use cases: create, get, list
    api/             routes, error handlers, request logging
    schemas.py       the wire and storage representation
    config.py        settings, main.py  application factory
  migrations/        Alembic
  tests/
frontend/
  app/               layout, page, error boundary, /api proxy
  components/        composer, booking sheet, ledger
  lib/               typed client, formatters, response types
```

The domain knows nothing about HTTP or SQL; the parser knows nothing about
pricing; the API owns its own schemas. Each of those boundaries is the reason a
change stays where it is put.

---

## The web UI

Three routes:

| | |
| --- | --- |
| `/` | Write a request, or build one from the rate card with dropdowns. The costed bill opens beside it. |
| `/bills` | Every bill on record, searchable by reference or by the words the request was written in. |
| `/bills/{id}` | One bill on its own page — server-rendered, so a shared link works on first paint. |

**The bill is the artefact.** It is laid out as a document — issuer, reference,
parties, line items, totals — and prints to a clean single-page A4 with a print
stylesheet that drops the navigation, composer and ledger. "Print or save PDF"
and "Copy link" sit above it.

**Every bill shows the request it was raised from**, verbatim, on screen and on
paper. A bill that has lost the words it came from cannot be checked against the
email that asked for it.

**The dropdown builder does not get its own endpoint.** It composes the English
sentence a person would have typed and posts that, so there is one ingestion
path, one set of rules, and a built bill still records a readable request.
`backend/tests/test_parser.py::TestComposedRequests` pins the exact sentence
shapes the builder produces, so the two cannot drift apart.

Money is set in tabular figures so columns line up. The palette is light only:
the main artefact is a printed document, and it should look the same on screen as
it does on paper.

The account control in the masthead is deliberately honest — this deployment has
no authentication, so it names the shared production-office session and says that
per-user sign-in arrives with auth on the API, rather than offering a button that
does nothing.

The browser never talks to the API directly. Next.js route handlers proxy the
three endpoints from the app's own origin, which keeps CORS out of the picture,
keeps the API host out of the client bundle, and lets the service sit on a
private network in a real deployment. The proxy is an allowlist, not a pass-through.

---

## What this deliberately does not do

- **No dates.** The service costs a length of stay, not a calendar range.
  `for 10 nights` works; `from 3 to 13 March` does not.
- **No availability.** It prices what was asked for; nothing checks whether the
  rooms exist at that location on those nights.
- **One currency**, set in the catalog.
- **No authentication.** Every bill belongs to one shared production-office
  account. The masthead says so rather than pretending otherwise.
- **No rate limiting.** It belongs at the edge, and it is not in the brief.

Given more time, the next three things would be idempotency keys on `POST`
(a double-submitted email should not become two bookings), amendment and
cancellation, and moving the rate card into the database with an effective date
so a historical quote can be re-derived rather than only replayed.
