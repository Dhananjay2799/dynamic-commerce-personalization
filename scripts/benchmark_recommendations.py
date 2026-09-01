from __future__ import annotations

import argparse
import json
import math
import statistics
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_OUTPUT = (
    REPO_ROOT
    / "benchmark-results"
    / "recommendations-local.json"
)

KNOWN_PRODUCT_ID = 4804056
KNOWN_CATEGORY_ID = 2053013554658804075


def request_json(
    method: str,
    url: str,
    payload: dict | None = None,
    timeout: float = 10.0,
) -> tuple[int, dict]:
    body = None

    headers = {
        "Accept": "application/json",
    }

    if payload is not None:
        body = json.dumps(
            payload
        ).encode("utf-8")

        headers[
            "Content-Type"
        ] = "application/json"

    request = Request(
        url=url,
        data=body,
        headers=headers,
        method=method,
    )

    try:
        with urlopen(
            request,
            timeout=timeout,
        ) as response:
            response_body = (
                response.read()
                .decode("utf-8")
            )

            return (
                response.status,
                json.loads(
                    response_body
                ),
            )

    except HTTPError as exc:
        response_body = (
            exc.read()
            .decode(
                "utf-8",
                errors="replace",
            )
        )

        raise RuntimeError(
            f"{method} {url} "
            f"returned HTTP "
            f"{exc.code}: "
            f"{response_body}"
        ) from exc

    except URLError as exc:
        raise RuntimeError(
            f"Unable to connect "
            f"to {url}: "
            f"{exc.reason}"
        ) from exc


def percentile(
    values: list[float],
    q: float,
) -> float:
    if not values:
        raise ValueError(
            "Cannot calculate "
            "percentile of "
            "empty values."
        )

    ordered = sorted(values)

    if len(ordered) == 1:
        return ordered[0]

    position = (
        len(ordered) - 1
    ) * q

    lower_index = math.floor(
        position
    )

    upper_index = math.ceil(
        position
    )

    if (
        lower_index
        == upper_index
    ):
        return ordered[
            lower_index
        ]

    lower_value = ordered[
        lower_index
    ]

    upper_value = ordered[
        upper_index
    ]

    fraction = (
        position
        - lower_index
    )

    return (
        lower_value
        + (
            upper_value
            - lower_value
        )
        * fraction
    )


def summarize(
    values: list[float],
) -> dict[str, float | int]:
    return {
        "count":
            len(values),

        "min_ms":
            round(
                min(values),
                3,
            ),

        "mean_ms":
            round(
                statistics.fmean(
                    values
                ),
                3,
            ),

        "median_ms":
            round(
                statistics.median(
                    values
                ),
                3,
            ),

        "p95_ms":
            round(
                percentile(
                    values,
                    0.95,
                ),
                3,
            ),

        "p99_ms":
            round(
                percentile(
                    values,
                    0.99,
                ),
                3,
            ),

        "max_ms":
            round(
                max(values),
                3,
            ),
    }


def get_recommendations(
    base_url: str,
    session_id: str,
    limit: int,
) -> dict:
    query = urlencode(
        {
            "session_id":
                session_id,
            "limit":
                limit,
        }
    )

    url = (
        f"{base_url}"
        "/api/v1/"
        "recommendations"
        f"?{query}"
    )

    started = (
        time.perf_counter()
    )

    status, payload = (
        request_json(
            method="GET",
            url=url,
        )
    )

    client_wall_ms = (
        time.perf_counter()
        - started
    ) * 1000

    if status != 200:
        raise RuntimeError(
            "Recommendation "
            "request failed."
        )

    payload[
        "_client_wall_ms"
    ] = client_wall_ms

    return payload


def main() -> None:
    parser = (
        argparse.ArgumentParser(
            description=(
                "Benchmark the local "
                "recommendation API."
            )
        )
    )

    parser.add_argument(
        "--base-url",
        default=(
            "http://127.0.0.1:8000"
        ),
    )

    parser.add_argument(
        "--iterations",
        type=int,
        default=500,
    )

    parser.add_argument(
        "--warmups",
        type=int,
        default=20,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=10,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    args = parser.parse_args()

    base_url = (
        args.base_url
        .rstrip("/")
    )

    if args.iterations < 1:
        raise ValueError(
            "--iterations must "
            "be at least 1."
        )

    if args.warmups < 0:
        raise ValueError(
            "--warmups cannot "
            "be negative."
        )

    session_id = (
        "benchmark-"
        + str(uuid.uuid4())
    )

    print(
        "Checking API health..."
    )

    status, health = (
        request_json(
            method="GET",
            url=(
                f"{base_url}"
                "/health"
            ),
        )
    )

    if (
        status != 200
        or health.get(
            "status"
        ) != "healthy"
    ):
        raise RuntimeError(
            "API health check "
            f"failed: {health}"
        )

    print(
        "Seeding personalized "
        "session intent..."
    )

    status, event = (
        request_json(
            method="POST",
            url=(
                f"{base_url}"
                "/api/v1/events"
            ),
            payload={
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
                        "latency_benchmark"
                },
            },
        )
    )

    if status != 201:
        raise RuntimeError(
            "Unable to seed "
            "benchmark session."
        )

    if not event.get(
        "online_state_updated"
    ):
        raise RuntimeError(
            "Redis online state "
            "was not updated."
        )

    print(
        "Measuring first "
        "recommendation request..."
    )

    first = get_recommendations(
        base_url=base_url,
        session_id=session_id,
        limit=args.limit,
    )

    if (
        first.get("strategy")
        != "session_intent"
    ):
        raise RuntimeError(
            "Benchmark did not "
            "enter personalized "
            "session_intent mode."
        )

    print(
        f"Running "
        f"{args.warmups} "
        "warm-up requests..."
    )

    for _ in range(
        args.warmups
    ):
        get_recommendations(
            base_url=base_url,
            session_id=session_id,
            limit=args.limit,
        )

    inference_values = []
    total_values = []
    client_values = []

    print(
        f"Running "
        f"{args.iterations} "
        "measured requests..."
    )

    for index in range(
        args.iterations
    ):
        response = (
            get_recommendations(
                base_url=base_url,
                session_id=session_id,
                limit=args.limit,
            )
        )

        if (
            response.get(
                "strategy"
            )
            != "session_intent"
        ):
            raise RuntimeError(
                "Strategy changed "
                "during benchmark."
            )

        inference_values.append(
            float(
                response[
                    "inference_ms"
                ]
            )
        )

        total_values.append(
            float(
                response[
                    "total_ms"
                ]
            )
        )

        client_values.append(
            float(
                response[
                    "_client_wall_ms"
                ]
            )
        )

        completed = (
            index + 1
        )

        if (
            completed % 100
            == 0
        ):
            print(
                f"  {completed}/"
                f"{args.iterations}"
            )

    result = {
        "benchmark":
            "recommendation_api_local",

        "captured_at_utc":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "base_url":
            base_url,

        "session_id":
            session_id,

        "model_version":
            first.get(
                "model_version"
            ),

        "strategy":
            first.get(
                "strategy"
            ),

        "recommendation_limit":
            args.limit,

        "warmup_requests":
            args.warmups,

        "measured_requests":
            args.iterations,

        "seed_event": {
            "event_type":
                "add_to_cart",

            "product_id":
                KNOWN_PRODUCT_ID,

            "weight":
                4.0,
        },

        "first_request_after_api_restart": {
            "inference_ms":
                round(
                    float(
                        first[
                            "inference_ms"
                        ]
                    ),
                    3,
                ),

            "total_ms":
                round(
                    float(
                        first[
                            "total_ms"
                        ]
                    ),
                    3,
                ),

            "client_wall_ms":
                round(
                    float(
                        first[
                            "_client_wall_ms"
                        ]
                    ),
                    3,
                ),
        },

        "warm_measurements": {
            "model_inference":
                summarize(
                    inference_values
                ),

            "server_total":
                summarize(
                    total_values
                ),

            "client_wall":
                summarize(
                    client_values
                ),
        },
    }

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.output.write_text(
        json.dumps(
            result,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print(
        "Benchmark complete."
    )

    print(
        json.dumps(
            result[
                "first_request_after_api_restart"
            ],
            indent=2,
        )
    )

    print()
    print(
        "Warm model inference:"
    )

    print(
        json.dumps(
            result[
                "warm_measurements"
            ][
                "model_inference"
            ],
            indent=2,
        )
    )

    print()
    print(
        "Warm server total:"
    )

    print(
        json.dumps(
            result[
                "warm_measurements"
            ][
                "server_total"
            ],
            indent=2,
        )
    )

    print()
    print(
        "Warm client wall:"
    )

    print(
        json.dumps(
            result[
                "warm_measurements"
            ][
                "client_wall"
            ],
            indent=2,
        )
    )

    print()
    print(
        "Saved:"
    )

    print(
        args.output.resolve()
    )


if __name__ == "__main__":
    main()