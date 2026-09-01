import pytest

from app.recommendations.intent import (
    build_product_weights,
    get_event_signal_weight,
)


PRODUCT_ID = 4804056


def make_event(
    event_type: str,
    product_id: int = PRODUCT_ID,
    metadata: dict | None = None,
) -> dict:
    return {
        "event_type": event_type,
        "product_id": product_id,
        "metadata": metadata or {},
    }


def test_add_to_cart_has_strong_positive_weight():
    events = [
        make_event(
            "add_to_cart"
        )
    ]

    weights = build_product_weights(
        events
    )

    assert weights == {
        PRODUCT_ID: 4.0
    }


def test_remove_from_cart_reduces_prior_cart_intent():
    events = [
        make_event(
            "add_to_cart"
        ),
        make_event(
            "remove_from_cart"
        ),
    ]

    weights = build_product_weights(
        events
    )

    # 4.0 * 0.92 - 2.0
    assert weights[
        PRODUCT_ID
    ] == pytest.approx(
        1.68,
        abs=0.0001,
    )


def test_impressions_do_not_create_product_intent():
    events = [
        make_event(
            "product_impression"
        ),
        make_event(
            "product_impression",
            product_id=1005115,
        ),
    ]

    weights = build_product_weights(
        events
    )

    assert weights == {}


def test_impressions_do_not_advance_recency_decay():
    baseline_events = [
        make_event(
            "add_to_cart"
        )
    ]

    events_with_impressions = [
        make_event(
            "add_to_cart"
        ),
        make_event(
            "product_impression",
            product_id=1004856,
        ),
        make_event(
            "product_impression",
            product_id=1005115,
        ),
        make_event(
            "product_impression",
            product_id=1004767,
        ),
    ]

    baseline = (
        build_product_weights(
            baseline_events
        )
    )

    with_impressions = (
        build_product_weights(
            events_with_impressions
        )
    )

    assert baseline == {
        PRODUCT_ID: 4.0
    }

    assert (
        with_impressions
        == baseline
    )


def test_search_event_does_not_advance_product_recency():
    events = [
        make_event(
            "product_click"
        ),
        {
            "event_type": "search",
            "product_id": None,
            "metadata": {
                "query": "apple"
            },
        },
    ]

    weights = build_product_weights(
        events
    )

    assert weights == {
        PRODUCT_ID: 1.5
    }


def test_more_recent_signal_receives_more_influence():
    first_product = 4804056
    second_product = 1005115

    events = [
        make_event(
            "product_click",
            product_id=first_product,
        ),
        make_event(
            "product_click",
            product_id=second_product,
        ),
    ]

    weights = build_product_weights(
        events
    )

    assert (
        weights[
            second_product
        ]
        >
        weights[
            first_product
        ]
    )

    assert weights[
        first_product
    ] == pytest.approx(
        1.38,
        abs=0.0001,
    )

    assert weights[
        second_product
    ] == pytest.approx(
        1.5,
        abs=0.0001,
    )


def test_dwell_time_uses_milliseconds():
    event = make_event(
        "dwell_time",
        metadata={
            "dwell_time_ms":
                5000
        },
    )

    weight = (
        get_event_signal_weight(
            event
        )
    )

    assert weight > 0
    assert weight <= 2.5


def test_long_dwell_time_is_capped():
    event = make_event(
        "dwell_time",
        metadata={
            "dwell_time_ms":
                600_000
        },
    )

    weight = (
        get_event_signal_weight(
            event
        )
    )

    assert weight == 2.5


@pytest.mark.parametrize(
    (
        "depth",
        "expected",
    ),
    [
        (0.25, 0.375),
        (0.50, 0.75),
        (0.75, 1.125),
        (1.00, 1.5),
    ],
)
def test_scroll_depth_weight(
    depth: float,
    expected: float,
):
    event = make_event(
        "scroll_depth",
        metadata={
            "depth": depth
        },
    )

    weight = (
        get_event_signal_weight(
            event
        )
    )

    assert weight == pytest.approx(
        expected
    )


def test_scroll_depth_is_clamped_to_one():
    event = make_event(
        "scroll_depth",
        metadata={
            "depth": 5.0
        },
    )

    weight = (
        get_event_signal_weight(
            event
        )
    )

    assert weight == 1.5


def test_unknown_events_have_zero_weight():
    event = make_event(
        "something_unknown"
    )

    assert (
        get_event_signal_weight(
            event
        )
        == 0.0
    )


def test_negative_only_signal_is_not_returned():
    events = [
        make_event(
            "remove_from_cart"
        )
    ]

    weights = build_product_weights(
        events
    )

    assert weights == {}