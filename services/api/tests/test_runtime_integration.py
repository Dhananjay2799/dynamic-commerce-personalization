from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


pytestmark = pytest.mark.integration


KNOWN_PRODUCT_ID = 4804056
KNOWN_CATEGORY_ID = (
    2053013554658804075
)


@pytest.fixture(
    scope="module"
)
def client():
    with TestClient(
        app
    ) as test_client:
        yield test_client


@pytest.fixture()
def session_id():
    return (
        "integration-"
        + str(uuid4())
    )


def test_health_reports_real_services_healthy(
    client,
):
    response = client.get(
        "/health"
    )

    assert (
        response.status_code
        == 200
    )

    data = response.json()

    assert (
        data["status"]
        == "healthy"
    )

    assert (
        data["services"][
            "postgres"
        ]
        == "healthy"
    )

    assert (
        data["services"][
            "redis"
        ]
        == "healthy"
    )


def test_real_event_updates_postgres_and_redis(
    client,
    session_id,
):
    response = client.post(
        "/api/v1/events",
        json={
            "session_id":
                session_id,

            "event_type":
                "add_to_cart",

            "product_id":
                KNOWN_PRODUCT_ID,

            "category_id":
                KNOWN_CATEGORY_ID,

            "metadata": {
                "surface":
                    "pytest_integration"
            },
        },
    )

    assert (
        response.status_code
        == 201
    )

    data = response.json()

    assert (
        data["accepted"]
        is True
    )

    assert (
        data["persisted"]
        is True
    )

    assert (
        data[
            "online_state_updated"
        ]
        is True
    )

    assert (
        data["event_type"]
        == "add_to_cart"
    )


def test_real_cart_event_creates_online_intent(
    client,
    session_id,
):
    event_response = (
        client.post(
            "/api/v1/events",
            json={
                "session_id":
                    session_id,

                "event_type":
                    "add_to_cart",

                "product_id":
                    KNOWN_PRODUCT_ID,

                "category_id":
                    KNOWN_CATEGORY_ID,

                "metadata": {
                    "surface":
                        "pytest_integration"
                },
            },
        )
    )

    assert (
        event_response.status_code
        == 201
    )

    intent_response = (
        client.get(
            (
                "/api/v1/sessions/"
                f"{session_id}"
                "/intent"
            )
        )
    )

    assert (
        intent_response.status_code
        == 200
    )

    data = (
        intent_response.json()
    )

    assert (
        data["event_count"]
        >= 1
    )

    signals = {
        signal["product_id"]:
            signal["weight"]
        for signal
        in data[
            "active_product_signals"
        ]
    }

    assert (
        KNOWN_PRODUCT_ID
        in signals
    )

    assert (
        signals[
            KNOWN_PRODUCT_ID
        ]
        == pytest.approx(
            4.0,
            abs=0.0001,
        )
    )


def test_real_recommendation_pipeline(
    client,
    session_id,
):
    event_response = (
        client.post(
            "/api/v1/events",
            json={
                "session_id":
                    session_id,

                "event_type":
                    "add_to_cart",

                "product_id":
                    KNOWN_PRODUCT_ID,

                "category_id":
                    KNOWN_CATEGORY_ID,

                "metadata": {
                    "surface":
                        "pytest_integration"
                },
            },
        )
    )

    assert (
        event_response.status_code
        == 201
    )

    response = client.get(
        "/api/v1/recommendations",
        params={
            "session_id":
                session_id,
            "limit": 10,
        },
    )

    assert (
        response.status_code
        == 200
    )

    data = response.json()

    assert (
        data["strategy"]
        == "session_intent"
    )

    assert (
        data["model_version"]
        == "session-svd-v3"
    )

    assert (
        len(
            data["items"]
        )
        == 10
    )

    returned_ids = {
        item["product"][
            "product_id"
        ]
        for item
        in data["items"]
    }

    assert (
        KNOWN_PRODUCT_ID
        not in returned_ids
    )

    assert (
        data[
            "inference_ms"
        ]
        >= 0
    )

    assert (
        data["total_ms"]
        >= data[
            "inference_ms"
        ]
    )


def test_real_add_then_remove_reduces_intent(
    client,
    session_id,
):
    add_response = client.post(
        "/api/v1/events",
        json={
            "session_id":
                session_id,

            "event_type":
                "add_to_cart",

            "product_id":
                KNOWN_PRODUCT_ID,

            "category_id":
                KNOWN_CATEGORY_ID,

            "metadata": {
                "surface":
                    "pytest_integration"
            },
        },
    )

    assert (
        add_response.status_code
        == 201
    )

    after_add = client.get(
        (
            "/api/v1/sessions/"
            f"{session_id}"
            "/intent"
        )
    ).json()

    add_weight = next(
        signal["weight"]
        for signal
        in after_add[
            "active_product_signals"
        ]
        if signal[
            "product_id"
        ]
        == KNOWN_PRODUCT_ID
    )

    remove_response = (
        client.post(
            "/api/v1/events",
            json={
                "session_id":
                    session_id,

                "event_type":
                    "remove_from_cart",

                "product_id":
                    KNOWN_PRODUCT_ID,

                "category_id":
                    KNOWN_CATEGORY_ID,

                "metadata": {
                    "surface":
                        "pytest_integration"
                },
            },
        )
    )

    assert (
        remove_response.status_code
        == 201
    )

    after_remove = client.get(
        (
            "/api/v1/sessions/"
            f"{session_id}"
            "/intent"
        )
    ).json()

    remove_weight = next(
        signal["weight"]
        for signal
        in after_remove[
            "active_product_signals"
        ]
        if signal[
            "product_id"
        ]
        == KNOWN_PRODUCT_ID
    )

    assert (
        add_weight
        == pytest.approx(
            4.0,
            abs=0.0001,
        )
    )

    assert (
        remove_weight
        == pytest.approx(
            1.68,
            abs=0.0001,
        )
    )

    assert (
        remove_weight
        < add_weight
    )
