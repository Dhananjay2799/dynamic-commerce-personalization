from __future__ import annotations

import argparse
import asyncio
from decimal import Decimal
from pathlib import Path
import polars as pl
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert

from app.core.database import AsyncSessionLocal
from app.models.category import Category
from app.models.product import Product


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed PostgreSQL with the processed e-commerce catalog."
    )
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--category-stats", type=Path, required=True)
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete existing products/categories first.",
    )
    return parser.parse_args()


def validate_paths(args: argparse.Namespace) -> None:
    if not args.catalog.exists():
        raise FileNotFoundError(f"Catalog not found: {args.catalog}")
    if not args.category_stats.exists():
        raise FileNotFoundError(
            f"Category statistics not found: {args.category_stats}"
        )


def clean_label(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def title_case_token(value: str | None) -> str | None:
    value = clean_label(value)
    if value is None:
        return None
    return value.replace("_", " ").replace("-", " ").title()


def build_product_name(
    brand: str | None, category_leaf: str | None, product_id: int
) -> str:
    brand_label = title_case_token(brand)
    category_label = title_case_token(category_leaf)
    parts = [part for part in (brand_label, category_label) if part]
    if not parts:
        parts.append("Product")
    return " ".join(parts) + f" #{product_id}"


def deterministic_inventory(product_id: int) -> int:
    return 20 + (product_id % 181)


def decimal_value(value: float | int) -> Decimal:
    return Decimal(str(round(float(value), 2)))


def build_categories(
    catalog: pl.DataFrame, category_stats: pl.DataFrame
) -> list[dict]:
    metadata = catalog.group_by("category_id").agg(
        pl.col("category_code").drop_nulls().first().alias("category_code"),
        pl.col("category_l1").drop_nulls().first().alias("category_l1"),
        pl.col("category_leaf").drop_nulls().first().alias("category_leaf"),
    )
    stats = (
        category_stats.group_by("category_id")
        .agg(
            pl.col("total_events").sum().alias("total_events"),
            pl.col("views").sum().alias("views"),
            pl.col("carts").sum().alias("carts"),
            pl.col("purchases").sum().alias("purchases"),
            pl.col("unique_products").max().alias("unique_products"),
            pl.col("unique_users").max().alias("unique_users"),
        )
        .with_columns(
            pl.when(pl.col("views") > 0)
            .then(pl.col("purchases") / pl.col("views"))
            .otherwise(0.0)
            .alias("view_to_purchase_rate")
        )
    )
    combined = metadata.join(stats, on="category_id", how="left").with_columns(
        pl.col("total_events").fill_null(0),
        pl.col("views").fill_null(0),
        pl.col("carts").fill_null(0),
        pl.col("purchases").fill_null(0),
        pl.col("unique_products").fill_null(0),
        pl.col("unique_users").fill_null(0),
        pl.col("view_to_purchase_rate").fill_null(0.0),
    )
    return combined.to_dicts()


def build_products(catalog: pl.DataFrame) -> list[dict]:
    products: list[dict] = []
    for row in catalog.iter_rows(named=True):
        product_id = int(row["product_id"])
        products.append(
            {
                "product_id": product_id,
                "category_id": int(row["category_id"]),
                "name": build_product_name(
                    row["brand"], row["category_leaf"], product_id
                ),
                "category_code": row["category_code"],
                "category_l1": row["category_l1"],
                "category_leaf": row["category_leaf"],
                "brand": row["brand"],
                "price": decimal_value(row["price"]),
                "inventory_quantity": deterministic_inventory(product_id),
                "image_url": None,
                "total_events": int(row["total_events"]),
                "views": int(row["views"]),
                "carts": int(row["carts"]),
                "removes": int(row["removes"]),
                "purchases": int(row["purchases"]),
                "unique_users": int(row["unique_users"]),
                "unique_sessions": int(row["unique_sessions"]),
                "average_price": decimal_value(row["average_price"]),
                "median_price": decimal_value(row["median_price"]),
                "min_price": decimal_value(row["min_price"]),
                "max_price": decimal_value(row["max_price"]),
                "view_to_purchase_rate": float(row["view_to_purchase_rate"]),
                "view_to_cart_rate": float(row["view_to_cart_rate"]),
                "last_event_time": row["last_event_time"],
            }
        )
    return products


async def upsert_batches(
    model, records: list[dict], batch_size: int = 1000
) -> None:
    async with AsyncSessionLocal() as session:
        for start in range(0, len(records), batch_size):
            batch = records[start : start + batch_size]
            statement = insert(model).values(batch)
            update_columns = {
                column.name: getattr(statement.excluded, column.name)
                for column in model.__table__.columns
                if not column.primary_key
            }
            statement = statement.on_conflict_do_update(
                index_elements=[list(model.__table__.primary_key.columns)[0].name],
                set_=update_columns,
            )
            await session.execute(statement)
            await session.commit()
            completed = min(start + batch_size, len(records))
            print(f"  {model.__tablename__}: {completed}/{len(records)}")


async def clear_existing_data() -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Product))
        await session.execute(delete(Category))
        await session.commit()


async def seed(args: argparse.Namespace) -> None:
    print("Reading processed catalog...")
    catalog = pl.read_parquet(args.catalog)
    category_stats = pl.read_parquet(args.category_stats)
    print(f"Catalog products: {catalog.height:,}")

    categories = build_categories(catalog, category_stats)
    products = build_products(catalog)
    print(f"Categories: {len(categories):,}")

    if args.replace:
        print("Removing existing catalog...")
        await clear_existing_data()

    print("Seeding categories...")
    await upsert_batches(Category, categories)

    print("Seeding products...")
    await upsert_batches(Product, products)

    print("\n* Catalog seed complete.")


def main() -> None:
    args = parse_args()
    validate_paths(args)
    asyncio.run(seed(args))


if __name__ == "__main__":
    main()