from __future__ import annotations

from math import log1p
from typing import Any


BASE_EVENT_WEIGHTS: dict[str, float] = {
    "product_impression": 0.0,
    "view_item": 1.0,
    "product_click": 1.5,
    "add_to_cart": 4.0,
    "remove_from_cart": -2.0,
    "purchase": 6.0,
}

RECENCY_DECAY = 0.92
MIN_SIGNAL_WEIGHT = 0.05


def _get_metadata(
    event: dict[str, Any],
) -> dict[str, Any]:
    metadata = event.get("metadata", {})

    if isinstance(metadata, dict):
        return metadata

    return {}


def _get_dwell_weight(
    event: dict[str, Any],
) -> float:
    metadata = _get_metadata(event)

    seconds = metadata.get("seconds")

    if seconds is None:
        milliseconds = metadata.get(
            "dwell_time_ms"
        )

        if milliseconds is not None:
            try:
                seconds = (
                    float(milliseconds)
                    / 1000.0
                )
            except (
                TypeError,
                ValueError,
            ):
                seconds = 0.0

    try:
        seconds_value = max(
            0.0,
            float(seconds or 0.0),
        )
    except (
        TypeError,
        ValueError,
    ):
        seconds_value = 0.0

    return min(
        2.5,
        log1p(seconds_value)
        / 1.5,
    )


def _get_scroll_weight(
    event: dict[str, Any],
) -> float:
    metadata = _get_metadata(event)

    depth = metadata.get(
        "depth",
        metadata.get(
            "scroll_depth",
            0.0,
        ),
    )

    try:
        depth_value = float(depth)
    except (
        TypeError,
        ValueError,
    ):
        depth_value = 0.0

    depth_value = max(
        0.0,
        min(
            1.0,
            depth_value,
        ),
    )

    return 1.5 * depth_value


def get_event_signal_weight(
    event: dict[str, Any],
) -> float:
    event_type = event.get(
        "event_type"
    )

    if event_type == "dwell_time":
        return _get_dwell_weight(
            event
        )

    if event_type == "scroll_depth":
        return _get_scroll_weight(
            event
        )

    if not isinstance(
        event_type,
        str,
    ):
        return 0.0

    return BASE_EVENT_WEIGHTS.get(
        event_type,
        0.0,
    )


def build_product_weights(
    events: list[
        dict[str, Any]
    ],
) -> dict[int, float]:
    weighted_events: list[
        tuple[int, float]
    ] = []

    for event in events:
        product_id = event.get(
            "product_id"
        )

        if product_id is None:
            continue

        signal_weight = (
            get_event_signal_weight(
                event
            )
        )

        # Analytics-only signals such
        # as impressions must not
        # advance the intent recency
        # clock.
        if signal_weight == 0.0:
            continue

        try:
            normalized_product_id = int(
                product_id
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

        weighted_events.append(
            (
                normalized_product_id,
                signal_weight,
            )
        )

    product_weights: dict[
        int,
        float,
    ] = {}

    event_count = len(
        weighted_events
    )

    for index, (
        product_id,
        signal_weight,
    ) in enumerate(
        weighted_events
    ):
        events_from_end = (
            event_count
            - index
            - 1
        )

        recency_weight = (
            RECENCY_DECAY
            ** events_from_end
        )

        weighted_signal = (
            signal_weight
            * recency_weight
        )

        product_weights[
            product_id
        ] = (
            product_weights.get(
                product_id,
                0.0,
            )
            + weighted_signal
        )

    return {
        product_id: round(
            weight,
            4,
        )
        for product_id, weight
        in product_weights.items()
        if weight
        > MIN_SIGNAL_WEIGHT
    }