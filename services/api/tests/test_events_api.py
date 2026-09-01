from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db
from app.main import app


TEST_SESSION_ID = (
    "test-session-12345678"
)

TEST_EVENT_ID = uuid4()


async def override_get_db():
    yield object()


@pytest.fixture()
def client():
    app.dependency_overrides[
        get_db
    ] = override_get_db

    test_client = TestClient(
        app
    )

    yield test_client

    test_client.close()

    app.dependency_overrides.clear()


@pytest.fixture()
def successful_persistence(
    monkeypatch,
):
    async def fake_persist_event(
        db,
        event,
    ):
        return SimpleNamespace(
            id=TEST_EVENT_ID
        )

    async def fake_update_online_state(
        event,
    ):
        return True

    monkeypatch.setattr(
        "app.api.events.persist_event",
        fake_persist_event,
    )

    monkeypatch.setattr(
        "app.api.events.update_online_state",
        fake_update_online_state,
    )


def test_valid_product_event_returns_201(
    client,
    successful_persistence,
):
    response = client.post(
        "/api/v1/events",
        json={
            "session_id":
                TEST_SESSION_ID,
            "event_type":
                "product_click",
            "product_id":
                4804056,
            "category_id":
                2053013554658804075,
            "metadata": {
                "surface":
                    "pytest"
            },
        },
    )

    assert (
        response.status_code
        == 201
    )


def test_event_response_contract(
    client,
    successful_persistence,
):
    response = client.post(
        "/api/v1/events",
        json={
            "session_id":
                TEST_SESSION_ID,
            "event_type":
                "add_to_cart",
            "product_id":
                4804056,
            "metadata": {},
        },
    )

    data = response.json()

    assert data == {
        "accepted": True,
        "event_id":
            str(TEST_EVENT_ID),
        "session_id":
            TEST_SESSION_ID,
        "event_type":
            "add_to_cart",
        "persisted": True,
        "online_state_updated":
            True,
    }


def test_search_event_does_not_require_product_id(
    client,
    successful_persistence,
):
    response = client.post(
        "/api/v1/events",
        json={
            "session_id":
                TEST_SESSION_ID,
            "event_type":
                "search",
            "metadata": {
                "query":
                    "apple headphones"
            },
        },
    )

    assert (
        response.status_code
        == 201
    )

    assert (
        response.json()[
            "event_type"
        ]
        == "search"
    )


def test_category_view_does_not_require_product_id(
    client,
    successful_persistence,
):
    response = client.post(
        "/api/v1/events",
        json={
            "session_id":
                TEST_SESSION_ID,
            "event_type":
                "category_view",
            "category_id":
                2053013554658804075,
            "metadata": {},
        },
    )

    assert (
        response.status_code
        == 201
    )


@pytest.mark.parametrize(
    "event_type",
    [
        "product_impression",
        "view_item",
        "product_click",
        "dwell_time",
        "scroll_depth",
        "add_to_cart",
        "remove_from_cart",
        "purchase",
    ],
)
def test_product_events_require_product_id(
    client,
    event_type,
):
    response = client.post(
        "/api/v1/events",
        json={
            "session_id":
                TEST_SESSION_ID,
            "event_type":
                event_type,
            "metadata": {},
        },
    )

    assert (
        response.status_code
        == 422
    )


def test_invalid_event_type_is_rejected(
    client,
):
    response = client.post(
        "/api/v1/events",
        json={
            "session_id":
                TEST_SESSION_ID,
            "event_type":
                "invalid_event",
            "product_id":
                4804056,
        },
    )

    assert (
        response.status_code
        == 422
    )


def test_short_session_id_is_rejected(
    client,
):
    response = client.post(
        "/api/v1/events",
        json={
            "session_id":
                "short",
            "event_type":
                "search",
            "metadata": {
                "query":
                    "apple"
            },
        },
    )

    assert (
        response.status_code
        == 422
    )


def test_redis_failure_does_not_lose_durable_event(
    client,
    monkeypatch,
):
    async def fake_persist_event(
        db,
        event,
    ):
        return SimpleNamespace(
            id=TEST_EVENT_ID
        )

    async def fake_update_online_state(
        event,
    ):
        return False

    monkeypatch.setattr(
        "app.api.events.persist_event",
        fake_persist_event,
    )

    monkeypatch.setattr(
        "app.api.events.update_online_state",
        fake_update_online_state,
    )

    response = client.post(
        "/api/v1/events",
        json={
            "session_id":
                TEST_SESSION_ID,
            "event_type":
                "product_click",
            "product_id":
                4804056,
            "metadata": {},
        },
    )

    assert (
        response.status_code
        == 201
    )

    data = response.json()

    assert (
        data["persisted"]
        is True
    )

    assert (
        data[
            "online_state_updated"
        ]
        is False
    )


def test_database_failure_returns_503(
    client,
    monkeypatch,
):
    async def fake_persist_event(
        db,
        event,
    ):
        raise RuntimeError(
            "database unavailable"
        )

    monkeypatch.setattr(
        "app.api.events.persist_event",
        fake_persist_event,
    )

    response = client.post(
        "/api/v1/events",
        json={
            "session_id":
                TEST_SESSION_ID,
            "event_type":
                "product_click",
            "product_id":
                4804056,
            "metadata": {},
        },
    )

    assert (
        response.status_code
        == 503
    )

    assert response.json() == {
        "detail":
            "Unable to persist telemetry event."
    }


def test_metadata_reaches_persistence_layer(
    client,
    monkeypatch,
):
    captured = {}

    async def fake_persist_event(
        db,
        event,
    ):
        captured["event"] = (
            event
        )

        return SimpleNamespace(
            id=TEST_EVENT_ID
        )

    async def fake_update_online_state(
        event,
    ):
        return True

    monkeypatch.setattr(
        "app.api.events.persist_event",
        fake_persist_event,
    )

    monkeypatch.setattr(
        "app.api.events.update_online_state",
        fake_update_online_state,
    )

    response = client.post(
        "/api/v1/events",
        json={
            "session_id":
                TEST_SESSION_ID,
            "event_type":
                "search",
            "metadata": {
                "query":
                    "apple",
                "surface":
                    "test_search",
            },
        },
    )

    assert (
        response.status_code
        == 201
    )

    event = captured[
        "event"
    ]

    assert (
        event.metadata[
            "query"
        ]
        == "apple"
    )

    assert (
        event.metadata[
            "surface"
        ]
        == "test_search"
    )