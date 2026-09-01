from app.recommendations.intent import (
    build_product_weights,
    get_active_category,
)
from app.recommendations.model import (
    get_recommendation_model,
)


def test_latest_category_view_becomes_active():
    events = [
        {
            "event_type": "category_view",
            "metadata": {
                "category": "electronics",
            },
        },
        {
            "event_type": "search",
            "metadata": {
                "query": "apple",
            },
        },
    ]

    assert (
        get_active_category(events)
        == "electronics"
    )


def test_latest_category_replaces_previous_category():
    events = [
        {
            "event_type": "category_view",
            "metadata": {
                "category": "electronics",
            },
        },
        {
            "event_type": "category_view",
            "metadata": {
                "category": "appliances",
            },
        },
    ]

    assert (
        get_active_category(events)
        == "appliances"
    )


def test_category_clear_removes_context():
    events = [
        {
            "event_type": "category_view",
            "metadata": {
                "category": "electronics",
            },
        },
        {
            "event_type": "category_view",
            "metadata": {
                "category": None,
                "cleared": True,
            },
        },
    ]

    assert (
        get_active_category(events)
        is None
    )


def test_category_view_does_not_change_product_weight():
    events = [
        {
            "event_type": "view_item",
            "product_id": 4804056,
            "metadata": {},
        },
        {
            "event_type": "category_view",
            "metadata": {
                "category": "electronics",
            },
        },
    ]

    weights = build_product_weights(
        events
    )

    assert (
        weights[4804056]
        == 1.0
    )


def test_category_context_limits_candidate_pool():
    model = get_recommendation_model()

    allowed = {
        int(product_id)
        for product_id
        in model.product_ids[:5]
    }

    strategy, candidates = (
        model.recommend(
            product_weights={},
            limit=10,
            candidate_product_ids=allowed,
        )
    )

    assert strategy == "popularity"

    assert candidates

    assert {
        candidate.product_id
        for candidate
        in candidates
    }.issubset(
        allowed
    )

    assert all(
        candidate.reason
        == "Popular in your current category"
        for candidate
        in candidates
    )
