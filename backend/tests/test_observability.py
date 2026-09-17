"""Request correlation: the id on the response must be the id in the log.

This is the pair that makes a support question answerable, so it is worth a test
rather than a glance at the console.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from io import StringIO

import pytest
from fastapi.testclient import TestClient

from app.api.observability import REQUEST_ID_HEADER, RequestIdFilter


@pytest.fixture
def captured_logs() -> Iterator[StringIO]:
    """A handler wired exactly as the application wires its own."""
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(logging.Formatter("[%(request_id)s] %(name)s %(message)s"))

    access = logging.getLogger("app.access")
    previous, previous_level = access.handlers, access.level
    access.handlers = [handler]
    access.setLevel(logging.INFO)
    try:
        yield stream
    finally:
        access.handlers, access.level = previous, previous_level


def test_every_response_carries_a_request_id(client: TestClient) -> None:
    response = client.get("/accommodations")

    assert response.headers[REQUEST_ID_HEADER]


def test_an_upstream_request_id_is_kept(client: TestClient) -> None:
    response = client.get(
        "/accommodations", headers={REQUEST_ID_HEADER: "trace-from-the-proxy"}
    )

    assert response.headers[REQUEST_ID_HEADER] == "trace-from-the-proxy"


def test_each_request_gets_its_own_id(client: TestClient) -> None:
    first = client.get("/accommodations").headers[REQUEST_ID_HEADER]
    second = client.get("/accommodations").headers[REQUEST_ID_HEADER]

    assert first != second


def test_the_access_log_is_tagged_with_that_same_id(
    client: TestClient, captured_logs: StringIO
) -> None:
    response = client.get("/accommodations", headers={REQUEST_ID_HEADER: "abc123"})

    logged = captured_logs.getvalue()
    assert "[abc123]" in logged
    assert "GET /accommodations 200" in logged
    assert response.headers[REQUEST_ID_HEADER] == "abc123"
