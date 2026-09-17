"""The HTTP contract, exercised against a real app and a real database."""

from __future__ import annotations

from fastapi.testclient import TestClient

BRIEF_SAMPLE = (
    "Book 3 double rooms and 1 suite for 10 nights with half board "
    "for the lead cast and director"
)


def book(client: TestClient, text: str = BRIEF_SAMPLE):
    return client.post("/accommodations", json={"text": text})


class TestCreate:
    def test_returns_201_and_a_booking_id(self, client: TestClient) -> None:
        response = book(client)

        assert response.status_code == 201
        assert response.json()["booking_id"]

    def test_returns_the_structured_request_it_read(self, client: TestClient) -> None:
        request = book(client).json()["request"]

        assert request["rooms"] == [
            {"room_type": "double", "quantity": 3},
            {"room_type": "suite", "quantity": 1},
        ]
        assert request["nights"] == 10
        assert request["meal_plan"] == "half_board"
        assert request["guests"] == 8
        assert request["guest_count_source"] == "derived_from_capacity"
        assert request["party"] == "the lead cast and director"

    def test_returns_the_computed_total(self, client: TestClient) -> None:
        quote = book(client).json()["quote"]

        assert quote["room_subtotal"] == "6100.00"
        assert quote["meal_subtotal"] == "2800.00"
        assert quote["subtotal"] == "8900.00"
        assert quote["discount"] == {
            "applied": True,
            "reason": "extended_stay",
            "threshold_nights": 7,
            "percent": "15",
            "amount": "1335.00",
        }
        assert quote["total"] == "7565.00"

    def test_returns_a_cost_breakdown_per_room(self, client: TestClient) -> None:
        rooms = book(client).json()["quote"]["rooms"]

        assert [room["room_type"] for room in rooms] == ["double", "suite"]
        assert rooms[0] == {
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
            "subtotal": "5700.00",
        }

    def test_keeps_the_text_exactly_as_it_arrived(self, client: TestClient) -> None:
        assert book(client).json()["raw_input"] == BRIEF_SAMPLE

    def test_money_is_sent_as_strings(self, client: TestClient) -> None:
        quote = book(client).json()["quote"]

        assert all(
            isinstance(quote[field], str)
            for field in ("room_subtotal", "meal_subtotal", "subtotal", "total")
        )

    def test_reports_assumptions_as_warnings(self, client: TestClient) -> None:
        warnings = book(client, "2 doubles for 5 days").json()["request"]["warnings"]

        assert any("as nights" in warning for warning in warnings)
        assert any("No meal plan mentioned" in warning for warning in warnings)

    def test_accepts_a_plain_text_body(self, client: TestClient) -> None:
        response = client.post(
            "/accommodations",
            content=BRIEF_SAMPLE.encode(),
            headers={"Content-Type": "text/plain"},
        )

        assert response.status_code == 201
        assert response.json()["quote"]["total"] == "7565.00"

    def test_each_booking_gets_its_own_id(self, client: TestClient) -> None:
        first, second = book(client).json(), book(client).json()

        assert first["booking_id"] != second["booking_id"]


class TestRetrieve:
    def test_reads_back_byte_for_byte(self, client: TestClient) -> None:
        created = book(client).json()

        fetched = client.get(f"/accommodations/{created['booking_id']}")

        assert fetched.status_code == 200
        assert fetched.json() == created

    def test_unknown_id_is_a_404(self, client: TestClient) -> None:
        response = client.get("/accommodations/does-not-exist")

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "booking_not_found"


class TestList:
    def test_is_empty_before_anything_is_booked(self, client: TestClient) -> None:
        body = client.get("/accommodations").json()

        assert body == {"items": [], "count": 0, "limit": 20, "offset": 0}

    def test_summarises_each_booking(self, client: TestClient) -> None:
        created = book(client).json()

        item = client.get("/accommodations").json()["items"][0]

        assert item["booking_id"] == created["booking_id"]
        assert item["raw_input"] == BRIEF_SAMPLE
        assert item["total"] == "7565.00"
        assert (item["nights"], item["guests"], item["room_count"]) == (10, 8, 4)
        assert item["meal_plan"] == "half_board"

    def test_newest_first(self, client: TestClient) -> None:
        book(client, "1 single for 2 nights")
        book(client, "1 suite for 3 nights")

        items = client.get("/accommodations").json()["items"]

        assert [item["raw_input"] for item in items] == [
            "1 suite for 3 nights",
            "1 single for 2 nights",
        ]

    def test_ordering_is_by_issue_sequence_not_by_clock(
        self, client: TestClient
    ) -> None:
        # Bookings raised in the same millisecond used to tie-break on a random
        # UUID, which made the ledger order non-deterministic.
        references = [
            book(client, "1 single for 2 nights").json()["reference"] for _ in range(6)
        ]

        page = client.get("/accommodations").json()
        listed = [item["reference"] for item in page["items"]]

        assert listed == list(reversed(references))

    def test_paginates(self, client: TestClient) -> None:
        for index in range(5):
            book(client, f"{index + 1} singles for 2 nights")

        page = client.get("/accommodations", params={"limit": 2, "offset": 2}).json()

        assert page["count"] == 5
        assert len(page["items"]) == 2
        assert (page["limit"], page["offset"]) == (2, 2)

    def test_rejects_an_out_of_range_page_size(self, client: TestClient) -> None:
        response = client.get("/accommodations", params={"limit": 500})

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "invalid_payload"


class TestRejectedRequests:
    def test_text_with_no_room_type(self, client: TestClient) -> None:
        response = book(client, "we need somewhere to sleep for 4 nights")

        assert response.status_code == 422
        error = response.json()["error"]
        assert error["code"] == "no_rooms_found"
        assert "dormitory" in error["hint"]

    def test_text_with_no_duration(self, client: TestClient) -> None:
        response = book(client, "book a suite for the director")

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "no_duration_found"

    def test_more_guests_than_beds(self, client: TestClient) -> None:
        response = book(client, "1 double for 3 nights for 6 people")

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "insufficient_capacity"

    def test_an_empty_body(self, client: TestClient) -> None:
        response = client.post(
            "/accommodations", content=b"", headers={"Content-Type": "text/plain"}
        )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "invalid_payload"

    def test_a_json_body_without_text(self, client: TestClient) -> None:
        response = client.post("/accommodations", json={"note": "3 doubles"})

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "invalid_payload"

    def test_nothing_is_stored_when_a_request_is_rejected(
        self, client: TestClient
    ) -> None:
        book(client, "we need somewhere to sleep for 4 nights")

        assert client.get("/accommodations").json()["count"] == 0

    def test_every_error_uses_the_same_envelope(self, client: TestClient) -> None:
        responses = [
            book(client, "nothing bookable here"),
            client.get("/accommodations/nope"),
            client.post("/accommodations", json={}),
        ]

        for response in responses:
            body = response.json()
            assert set(body) == {"error"}
            assert set(body["error"]) == {"code", "message", "hint"}
            assert body["error"]["message"].endswith(".")


class TestService:
    def test_health_reports_the_database(self, client: TestClient) -> None:
        assert client.get("/health").json() == {
            "status": "ok",
            "database": "reachable",
        }

    def test_publishes_an_openapi_document(self, client: TestClient) -> None:
        schema = client.get("/openapi.json").json()

        assert "/accommodations" in schema["paths"]
        assert "/accommodations/{booking_id}" in schema["paths"]
        body = schema["paths"]["/accommodations"]["post"]["requestBody"]
        assert set(body["content"]) == {"application/json", "text/plain"}


class TestBillReference:
    def test_a_booking_gets_a_readable_bill_reference(self, client: TestClient) -> None:
        booking = book(client).json()

        assert booking["reference"].startswith("ACM-")
        assert booking["reference"].endswith("-00001")

    def test_references_run_in_sequence(self, client: TestClient) -> None:
        references = [
            book(client, "1 single for 2 nights").json()["reference"] for _ in range(3)
        ]

        assert [reference[-5:] for reference in references] == ["00001", "00002", "00003"]

    def test_the_listing_shows_the_same_reference(self, client: TestClient) -> None:
        created = book(client).json()

        item = client.get("/accommodations").json()["items"][0]

        assert item["reference"] == created["reference"]

    def test_the_reference_survives_a_round_trip(self, client: TestClient) -> None:
        created = book(client).json()

        fetched = client.get(f"/accommodations/{created['booking_id']}").json()

        assert fetched["reference"] == created["reference"]
