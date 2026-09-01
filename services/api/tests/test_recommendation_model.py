import math

import pytest

from app.recommendations.model import (
    get_recommendation_model,
)


KNOWN_HEADPHONE_ID = 4804056

EXPECTED_COLD_START_TOP = [
    1004856,
    1004767,
    1005115,
]

EXPECTED_HEADPHONE_TOP = [
    4802036,
    4804572,
]


@pytest.fixture(scope="module")
def model():
    return get_recommendation_model()


def test_model_version(model):
    assert (
        model.MODEL_VERSION
        == "session-svd-v2"
    )


def test_cold_start_uses_popularity(
    model,
):
    strategy, candidates = (
        model.recommend(
            product_weights={},
            limit=3,
        )
    )

    assert strategy == "popularity"

    assert len(candidates) == 3

    assert [
        candidate.product_id
        for candidate in candidates
    ] == EXPECTED_COLD_START_TOP


def test_cold_start_reason_is_correct(
    model,
):
    _, candidates = (
        model.recommend(
            product_weights={},
            limit=3,
        )
    )

    assert all(
        candidate.reason
        == "Popular with shoppers"
        for candidate in candidates
    )


def test_session_signal_switches_strategy(
    model,
):
    strategy, candidates = (
        model.recommend(
            product_weights={
                KNOWN_HEADPHONE_ID:
                    4.0
            },
            limit=10,
        )
    )

    assert (
        strategy
        == "session_intent"
    )

    assert len(candidates) == 10


def test_seen_product_is_excluded(
    model,
):
    _, candidates = (
        model.recommend(
            product_weights={
                KNOWN_HEADPHONE_ID:
                    4.0
            },
            limit=20,
        )
    )

    returned_ids = {
        candidate.product_id
        for candidate in candidates
    }

    assert (
        KNOWN_HEADPHONE_ID
        not in returned_ids
    )


def test_requested_limit_is_respected(
    model,
):
    for limit in [
        1,
        3,
        5,
        10,
    ]:
        _, candidates = (
            model.recommend(
                product_weights={
                    KNOWN_HEADPHONE_ID:
                        4.0
                },
                limit=limit,
            )
        )

        assert (
            len(candidates)
            == limit
        )


def test_candidate_ids_are_unique(
    model,
):
    _, candidates = (
        model.recommend(
            product_weights={
                KNOWN_HEADPHONE_ID:
                    4.0
            },
            limit=20,
        )
    )

    product_ids = [
        candidate.product_id
        for candidate in candidates
    ]

    assert len(product_ids) == len(
        set(product_ids)
    )


def test_candidates_exist_in_model_catalog(
    model,
):
    _, candidates = (
        model.recommend(
            product_weights={
                KNOWN_HEADPHONE_ID:
                    4.0
            },
            limit=20,
        )
    )

    catalog_ids = {
        int(product_id)
        for product_id
        in model.product_ids
    }

    assert all(
        candidate.product_id
        in catalog_ids
        for candidate in candidates
    )


def test_scores_are_finite(
    model,
):
    _, candidates = (
        model.recommend(
            product_weights={
                KNOWN_HEADPHONE_ID:
                    4.0
            },
            limit=20,
        )
    )

    assert all(
        math.isfinite(
            candidate.score
        )
        for candidate in candidates
    )


def test_scores_are_sorted_descending(
    model,
):
    _, candidates = (
        model.recommend(
            product_weights={
                KNOWN_HEADPHONE_ID:
                    4.0
            },
            limit=20,
        )
    )

    scores = [
        candidate.score
        for candidate in candidates
    ]

    assert scores == sorted(
        scores,
        reverse=True,
    )


def test_session_reason_is_correct(
    model,
):
    _, candidates = (
        model.recommend(
            product_weights={
                KNOWN_HEADPHONE_ID:
                    4.0
            },
            limit=10,
        )
    )

    assert all(
        candidate.reason
        == (
            "Based on your current "
            "session intent"
        )
        for candidate in candidates
    )


def test_known_headphone_signal_produces_expected_top_products(
    model,
):
    _, candidates = (
        model.recommend(
            product_weights={
                KNOWN_HEADPHONE_ID:
                    4.0
            },
            limit=5,
        )
    )

    top_two_ids = [
        candidate.product_id
        for candidate
        in candidates[:2]
    ]

    assert (
        top_two_ids
        == EXPECTED_HEADPHONE_TOP
    )


def test_recommendations_are_deterministic(
    model,
):
    weights = {
        KNOWN_HEADPHONE_ID:
            4.0
    }

    _, first = model.recommend(
        product_weights=weights,
        limit=10,
    )

    _, second = model.recommend(
        product_weights=weights,
        limit=10,
    )

    first_result = [
        (
            candidate.product_id,
            candidate.score,
        )
        for candidate in first
    ]

    second_result = [
        (
            candidate.product_id,
            candidate.score,
        )
        for candidate in second
    ]

    assert first_result == (
        second_result
    )


def test_stronger_signal_keeps_known_headphones_near_top(
    model,
):
    _, candidates = (
        model.recommend(
            product_weights={
                KNOWN_HEADPHONE_ID:
                    8.0
            },
            limit=5,
        )
    )

    top_ids = [
        candidate.product_id
        for candidate in candidates
    ]

    assert 4802036 in top_ids
    assert 4804572 in top_ids