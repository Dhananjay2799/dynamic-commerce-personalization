from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

import polars as pl


VALID_EVENT_TYPES = (
    "view",
    "cart",
    "remove_from_cart",
    "purchase",
)


RAW_SCHEMA = {
    "event_time": pl.String,
    "event_type": pl.String,
    "product_id": pl.Int64,
    "category_id": pl.Int64,
    "category_code": pl.String,
    "brand": pl.String,
    "price": pl.Float64,
    "user_id": pl.Int64,
    "user_session": pl.String,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a deterministic ML-ready sample from the "
            "multi-category e-commerce behavior dataset."
        )
    )

    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to the source CSV file.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for processed Parquet files.",
    )

    parser.add_argument(
        "--sample-modulus",
        type=int,
        default=100,
        help="Modulus used for deterministic user sampling.",
    )

    parser.add_argument(
        "--sample-buckets",
        type=int,
        default=2,
        help=(
            "Number of modulus buckets to retain. "
            "2 of 100 is approximately a 2%% user sample."
        ),
    )

    parser.add_argument(
        "--min-product-events",
        type=int,
        default=5,
        help="Minimum sampled interactions required for catalog products.",
    )

    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.input.exists():
        raise FileNotFoundError(
            f"Input dataset does not exist: {args.input}"
        )

    if args.sample_modulus <= 0:
        raise ValueError("--sample-modulus must be greater than zero.")

    if not 0 < args.sample_buckets <= args.sample_modulus:
        raise ValueError(
            "--sample-buckets must be between 1 and "
            "--sample-modulus."
        )

    if args.min_product_events < 1:
        raise ValueError(
            "--min-product-events must be at least 1."
        )


def build_event_weight() -> pl.Expr:
    return (
        pl.when(pl.col("event_type") == "view")
        .then(pl.lit(1.0))
        .when(pl.col("event_type") == "cart")
        .then(pl.lit(3.0))
        .when(pl.col("event_type") == "purchase")
        .then(pl.lit(5.0))
        .when(pl.col("event_type") == "remove_from_cart")
        .then(pl.lit(-1.0))
        .otherwise(pl.lit(0.0))
        .cast(pl.Float32)
        .alias("event_weight")
    )


def build_clean_events(
    input_path: Path,
    sample_modulus: int,
    sample_buckets: int,
) -> pl.LazyFrame:
    raw = pl.scan_csv(
        input_path,
        schema_overrides=RAW_SCHEMA,
    )

    sampled = raw.filter(
        pl.col("event_type").is_in(VALID_EVENT_TYPES)
        & pl.col("product_id").is_not_null()
        & pl.col("category_id").is_not_null()
        & pl.col("user_id").is_not_null()
        & pl.col("user_session").is_not_null()
        & pl.col("price").is_not_null()
        & (pl.col("price") > 0)
        & (
            (pl.col("user_id") % sample_modulus)
            < sample_buckets
        )
    )

    cleaned = (
        sampled
        .with_columns(
            pl.col("event_time")
            .str.to_datetime(
                "%Y-%m-%d %H:%M:%S %Z",
                strict=False,
            )
            .alias("event_time"),
            pl.col("brand")
            .str.to_lowercase()
            .alias("brand"),
        )
        .filter(
            pl.col("event_time").is_not_null()
        )
        .with_columns(
            pl.when(pl.col("category_code").is_not_null())
            .then(
                pl.col("category_code")
                .str.split(".")
                .list.first()
            )
            .otherwise(None)
            .alias("category_l1"),

            pl.when(pl.col("category_code").is_not_null())
            .then(
                pl.col("category_code")
                .str.split(".")
                .list.last()
            )
            .otherwise(None)
            .alias("category_leaf"),

            build_event_weight(),
        )
        .select(
            "event_time",
            "event_type",
            "event_weight",
            "product_id",
            "category_id",
            "category_code",
            "category_l1",
            "category_leaf",
            "brand",
            "price",
            "user_id",
            "user_session",
        )
    )

    return cleaned


def build_product_stats(
    events: pl.LazyFrame,
) -> pl.LazyFrame:
    return (
        events
        .group_by("product_id")
        .agg(
            pl.len().alias("total_events"),

            (pl.col("event_type") == "view")
            .sum()
            .alias("views"),

            (pl.col("event_type") == "cart")
            .sum()
            .alias("carts"),

            (pl.col("event_type") == "remove_from_cart")
            .sum()
            .alias("removes"),

            (pl.col("event_type") == "purchase")
            .sum()
            .alias("purchases"),

            pl.col("user_id")
            .n_unique()
            .alias("unique_users"),

            pl.col("user_session")
            .n_unique()
            .alias("unique_sessions"),

            pl.col("price")
            .mean()
            .round(2)
            .alias("average_price"),

            pl.col("price")
            .median()
            .round(2)
            .alias("median_price"),

            pl.col("price")
            .min()
            .round(2)
            .alias("min_price"),

            pl.col("price")
            .max()
            .round(2)
            .alias("max_price"),

            pl.col("event_time")
            .max()
            .alias("last_event_time"),
        )
        .with_columns(
            pl.when(pl.col("views") > 0)
            .then(
                pl.col("purchases")
                / pl.col("views")
            )
            .otherwise(0.0)
            .alias("view_to_purchase_rate"),

            pl.when(pl.col("views") > 0)
            .then(
                pl.col("carts")
                / pl.col("views")
            )
            .otherwise(0.0)
            .alias("view_to_cart_rate"),
        )
    )


def build_catalog(
    events: pl.LazyFrame,
    product_stats: pl.LazyFrame,
    min_product_events: int,
) -> pl.LazyFrame:
    metadata = (
        events
        .group_by("product_id")
        .agg(
            pl.col("category_id")
            .first()
            .alias("category_id"),

            pl.col("category_code")
            .drop_nulls()
            .first()
            .alias("category_code"),

            pl.col("category_l1")
            .drop_nulls()
            .first()
            .alias("category_l1"),

            pl.col("category_leaf")
            .drop_nulls()
            .first()
            .alias("category_leaf"),

            pl.col("brand")
            .drop_nulls()
            .first()
            .alias("brand"),

            pl.col("price")
            .median()
            .round(2)
            .alias("price"),
        )
    )

    return (
        metadata
        .join(
            product_stats,
            on="product_id",
            how="inner",
        )
        .filter(
            pl.col("total_events")
            >= min_product_events
        )
        .sort(
            "total_events",
            descending=True,
        )
    )


def build_category_stats(
    events: pl.LazyFrame,
) -> pl.LazyFrame:
    return (
        events
        .filter(
            pl.col("category_code").is_not_null()
        )
        .group_by(
            "category_id",
            "category_code",
            "category_l1",
            "category_leaf",
        )
        .agg(
            pl.len().alias("total_events"),

            (pl.col("event_type") == "view")
            .sum()
            .alias("views"),

            (pl.col("event_type") == "cart")
            .sum()
            .alias("carts"),

            (pl.col("event_type") == "purchase")
            .sum()
            .alias("purchases"),

            pl.col("product_id")
            .n_unique()
            .alias("unique_products"),

            pl.col("user_id")
            .n_unique()
            .alias("unique_users"),
        )
        .with_columns(
            pl.when(pl.col("views") > 0)
            .then(
                pl.col("purchases")
                / pl.col("views")
            )
            .otherwise(0.0)
            .alias("view_to_purchase_rate")
        )
        .sort(
            "total_events",
            descending=True,
        )
    )


def build_session_stats(
    events: pl.LazyFrame,
) -> pl.LazyFrame:
    return (
        events
        .group_by(
            "user_id",
            "user_session",
        )
        .agg(
            pl.col("event_time")
            .min()
            .alias("session_start"),

            pl.col("event_time")
            .max()
            .alias("session_end"),

            pl.len()
            .alias("event_count"),

            pl.col("product_id")
            .n_unique()
            .alias("unique_products"),

            pl.col("category_id")
            .n_unique()
            .alias("unique_categories"),

            (pl.col("event_type") == "view")
            .sum()
            .alias("views"),

            (pl.col("event_type") == "cart")
            .sum()
            .alias("carts"),

            (pl.col("event_type") == "remove_from_cart")
            .sum()
            .alias("removes"),

            (pl.col("event_type") == "purchase")
            .sum()
            .alias("purchases"),
        )
    )


def collect_summary(
    events: pl.LazyFrame,
    catalog: pl.LazyFrame,
) -> dict:
    event_summary = (
        events
        .select(
            pl.len().alias("events"),
            pl.col("user_id")
            .n_unique()
            .alias("users"),
            pl.col("user_session")
            .n_unique()
            .alias("sessions"),
            pl.col("product_id")
            .n_unique()
            .alias("products"),
            pl.col("category_id")
            .n_unique()
            .alias("categories"),
        )
        .collect(engine="streaming")
        .row(0, named=True)
    )

    event_types = (
        events
        .group_by("event_type")
        .agg(
            pl.len().alias("count")
        )
        .sort(
            "count",
            descending=True,
        )
        .collect(engine="streaming")
        .to_dicts()
    )

    catalog_count = (
        catalog
        .select(
            pl.len().alias("catalog_products")
        )
        .collect(engine="streaming")
        .item()
    )

    return {
        **event_summary,
        "catalog_products": catalog_count,
        "event_types": event_types,
    }


def main() -> None:
    args = parse_args()
    validate_args(args)

    args.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    events_path = args.output_dir / "events.parquet"
    product_stats_path = (
        args.output_dir / "product_stats.parquet"
    )
    catalog_path = args.output_dir / "catalog.parquet"
    category_stats_path = (
        args.output_dir / "category_stats.parquet"
    )
    sessions_path = (
        args.output_dir / "sessions.parquet"
    )
    summary_path = args.output_dir / "summary.json"

    print("=" * 72)
    print("Dynamic Commerce Personalization")
    print("Dataset preprocessing")
    print("=" * 72)

    print(f"Input: {args.input}")
    print(f"Output: {args.output_dir}")

    sample_percentage = (
        args.sample_buckets
        / args.sample_modulus
        * 100
    )

    print(
        "Deterministic user sample: "
        f"{sample_percentage:.2f}%"
    )

    started = perf_counter()

    print("\n[1/6] Building sampled event dataset...")

    clean_events = build_clean_events(
        input_path=args.input,
        sample_modulus=args.sample_modulus,
        sample_buckets=args.sample_buckets,
    )

    clean_events.sink_parquet(
        events_path,
        compression="zstd",
        statistics=True,
        maintain_order=True,
        engine="streaming",
    )

    events = pl.scan_parquet(events_path)

    print("[2/6] Building product statistics...")

    product_stats = build_product_stats(events)

    product_stats.sink_parquet(
        product_stats_path,
        compression="zstd",
        engine="streaming",
    )

    print("[3/6] Building product catalog...")

    catalog = build_catalog(
        events=events,
        product_stats=product_stats,
        min_product_events=args.min_product_events,
    )

    catalog.sink_parquet(
        catalog_path,
        compression="zstd",
        engine="streaming",
    )

    print("[4/6] Building category statistics...")

    category_stats = build_category_stats(events)

    category_stats.sink_parquet(
        category_stats_path,
        compression="zstd",
        engine="streaming",
    )

    print("[5/6] Building session statistics...")

    sessions = build_session_stats(events)

    sessions.sink_parquet(
        sessions_path,
        compression="zstd",
        engine="streaming",
    )

    print("[6/6] Building summary...")

    summary = collect_summary(
        events=events,
        catalog=catalog,
    )

    summary["sample_modulus"] = (
        args.sample_modulus
    )
    summary["sample_buckets"] = (
        args.sample_buckets
    )
    summary["sample_percentage"] = (
        sample_percentage
    )
    summary["min_product_events"] = (
        args.min_product_events
    )

    with summary_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            summary,
            file,
            indent=2,
        )

    elapsed = perf_counter() - started

    print("\n" + "=" * 72)
    print("Preprocessing complete")
    print("=" * 72)

    print(
        json.dumps(
            summary,
            indent=2,
        )
    )

    print("\nGenerated:")
    print(f"  {events_path}")
    print(f"  {product_stats_path}")
    print(f"  {catalog_path}")
    print(f"  {category_stats_path}")
    print(f"  {sessions_path}")
    print(f"  {summary_path}")

    print(
        f"\nElapsed seconds: {elapsed:.2f}"
    )


if __name__ == "__main__":
    main()