import math

import pytest
from fastapi.testclient import (
    TestClient,
)

from app.main import app


pytestmark = pytest.mark.integration


@pytest.fixture(
    scope="module"
)
def client():
    with TestClient(
        app
    ) as test_client:
        yield test_client


def test_categories_are_paginated(
    client: TestClient,
):
    response = client.get(
        (
            "/api/v1/categories"
            "?page=1"
            "&page_size=5"
        )
    )

    assert (
        response.status_code
        == 200
    )

    data = response.json()

    assert isinstance(
        data,
        dict,
    )

    assert len(
        data["items"]
    ) == 5

    assert (
        data["page"]
        == 1
    )

    assert (
        data["page_size"]
        == 5
    )

    assert (
        data["total"]
        >= 5
    )

    assert (
        data["total_pages"]
        == math.ceil(
            data["total"]
            / 5
        )
    )


def test_category_pages_do_not_overlap(
    client: TestClient,
):
    page_one = client.get(
        (
            "/api/v1/categories"
            "?page=1"
            "&page_size=5"
        )
    ).json()

    page_two = client.get(
        (
            "/api/v1/categories"
            "?page=2"
            "&page_size=5"
        )
    ).json()

    page_one_ids = {
        item["category_id"]
        for item
        in page_one["items"]
    }

    page_two_ids = {
        item["category_id"]
        for item
        in page_two["items"]
    }

    assert len(
        page_one_ids
    ) == 5

    assert len(
        page_two_ids
    ) == 5

    assert (
        page_one_ids
        .isdisjoint(
            page_two_ids
        )
    )


def test_inventory_is_paginated(
    client: TestClient,
):
    response = client.get(
        (
            "/api/v1/inventory"
            "?page=1"
            "&page_size=5"
        )
    )

    assert (
        response.status_code
        == 200
    )

    data = response.json()

    assert isinstance(
        data,
        dict,
    )

    assert len(
        data["items"]
    ) == 5

    assert (
        data["page"]
        == 1
    )

    assert (
        data["page_size"]
        == 5
    )

    assert (
        data["total"]
        >= 5
    )

    assert (
        data["total_pages"]
        == math.ceil(
            data["total"]
            / 5
        )
    )

    for item in data[
        "items"
    ]:
        assert (
            "inventory_quantity"
            in item
        )

        assert (
            item[
                "inventory_quantity"
            ]
            >= 0
        )


def test_inventory_low_stock_filter(
    client: TestClient,
):
    response = client.get(
        (
            "/api/v1/inventory"
            "?page=1"
            "&page_size=100"
            "&low_stock=true"
            "&low_stock_threshold=25"
        )
    )

    assert (
        response.status_code
        == 200
    )

    data = response.json()

    assert (
        data["total"]
        > 0
    )

    assert (
        len(
            data["items"]
        )
        <= 100
    )

    assert all(
        item[
            "inventory_quantity"
        ]
        <= 25
        for item
        in data["items"]
    )


def test_inventory_category_filter(
    client: TestClient,
):
    response = client.get(
        (
            "/api/v1/inventory"
            "?page=1"
            "&page_size=20"
            "&category=electronics"
        )
    )

    assert (
        response.status_code
        == 200
    )

    data = response.json()

    assert (
        data["total"]
        > 0
    )

    assert (
        len(
            data["items"]
        )
        > 0
    )

    for item in data[
        "items"
    ]:
        searchable_category = (
            " ".join(
                str(
                    item.get(
                        field
                    )
                    or ""
                )
                for field in (
                    "category_code",
                    "category_l1",
                    "category_leaf",
                )
            )
            .lower()
        )

        assert (
            "electronics"
            in searchable_category
        )