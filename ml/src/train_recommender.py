from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter

import joblib
import numpy as np
import polars as pl
from scipy.sparse import csr_matrix
from sklearn.decomposition import TruncatedSVD


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Train and evaluate popularity and SVD "
            "recommendation baselines."
        )
    )

    parser.add_argument(
        "--events",
        type=Path,
        required=True,
        help="Processed events.parquet path.",
    )

    parser.add_argument(
        "--catalog",
        type=Path,
        required=True,
        help="Processed catalog.parquet path.",
    )

    parser.add_argument(
        "--artifacts-dir",
        type=Path,
        required=True,
        help="Directory for trained artifacts.",
    )

    parser.add_argument(
        "--components",
        type=int,
        default=64,
        help="Number of SVD latent dimensions.",
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
    )

    parser.add_argument(
        "--max-eval-users",
        type=int,
        default=10_000,
        help=(
            "Maximum number of users used for "
            "offline evaluation."
        ),
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=256,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )

    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.events.exists():
        raise FileNotFoundError(
            f"Events file not found: {args.events}"
        )

    if not args.catalog.exists():
        raise FileNotFoundError(
            f"Catalog file not found: {args.catalog}"
        )

    if args.components < 2:
        raise ValueError(
            "--components must be at least 2."
        )

    if args.top_k < 1:
        raise ValueError(
            "--top-k must be at least 1."
        )

    if args.max_eval_users < 1:
        raise ValueError(
            "--max-eval-users must be at least 1."
        )


def load_data(
    events_path: Path,
    catalog_path: Path,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    print("Loading processed data...")

    events = pl.read_parquet(events_path)

    catalog = (
        pl.read_parquet(catalog_path)
        .select(
            "product_id",
            "category_id",
            "category_code",
            "brand",
            "price",
        )
        .unique(
            subset=["product_id"]
        )
        .sort("product_id")
    )

    catalog_ids = catalog[
        "product_id"
    ].to_list()

    events = (
        events
        .filter(
            pl.col("product_id")
            .is_in(catalog_ids)
        )
        .select(
            "event_time",
            "event_type",
            "event_weight",
            "product_id",
            "user_id",
            "user_session",
        )
        .sort(
            [
                "user_id",
                "event_time",
                "product_id",
            ]
        )
    )

    print(
        f"Catalog products: {catalog.height:,}"
    )

    print(
        f"Catalog interactions: {events.height:,}"
    )

    print(
        "Users: "
        f"{events['user_id'].n_unique():,}"
    )

    return events, catalog


def choose_evaluation_users(
    events: pl.DataFrame,
    max_users: int,
    seed: int,
) -> np.ndarray:
    eligible = (
        events
        .group_by("user_id")
        .agg(
            pl.col("product_id")
            .n_unique()
            .alias("distinct_products")
        )
        .filter(
            pl.col("distinct_products") >= 2
        )
        .select("user_id")
        .sort("user_id")
    )

    user_ids = eligible[
        "user_id"
    ].to_numpy()

    print(
        "Users with >=2 distinct products: "
        f"{len(user_ids):,}"
    )

    if len(user_ids) <= max_users:
        return user_ids

    rng = np.random.default_rng(seed)

    selected = rng.choice(
        user_ids,
        size=max_users,
        replace=False,
    )

    return np.sort(selected)


def build_temporal_holdout(
    events: pl.DataFrame,
    evaluation_users: np.ndarray,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    selected_events = (
        events
        .filter(
            pl.col("user_id")
            .is_in(
                evaluation_users.tolist()
            )
        )
        .sort(
            [
                "user_id",
                "event_time",
                "product_id",
            ]
        )
    )

    holdout = (
        selected_events
        .group_by(
            "user_id",
            maintain_order=True,
        )
        .agg(
            pl.col("product_id")
            .last()
            .alias("test_product_id"),

            pl.col("event_time")
            .last()
            .alias("test_event_time"),

            pl.col("event_type")
            .last()
            .alias("test_event_type"),
        )
    )

    train = (
        events
        .join(
            holdout.select(
                "user_id",
                "test_product_id",
            ),
            on="user_id",
            how="left",
        )
        .filter(
            pl.col(
                "test_product_id"
            ).is_null()
            |
            (
                pl.col("product_id")
                !=
                pl.col("test_product_id")
            )
        )
        .drop("test_product_id")
    )

    return train, holdout


def aggregate_training_strength(
    train: pl.DataFrame,
) -> pl.DataFrame:
    aggregated = (
        train
        .group_by(
            [
                "user_id",
                "product_id",
            ]
        )
        .agg(
            pl.col("event_weight")
            .sum()
            .alias("raw_strength"),

            pl.col("event_time")
            .max()
            .alias("last_interaction"),
        )
        .filter(
            pl.col("raw_strength") > 0
        )
        .with_columns(
            pl.col("raw_strength")
            .log1p()
            .cast(pl.Float32)
            .alias("strength")
        )
    )

    return aggregated


def filter_valid_holdout(
    holdout: pl.DataFrame,
    train_agg: pl.DataFrame,
) -> pl.DataFrame:
    observed_products = (
        train_agg["product_id"]
        .unique()
        .to_list()
    )

    train_users = (
        train_agg["user_id"]
        .unique()
        .to_list()
    )

    valid = (
        holdout
        .filter(
            pl.col("test_product_id")
            .is_in(observed_products)
        )
        .filter(
            pl.col("user_id")
            .is_in(train_users)
        )
        .sort("user_id")
    )

    return valid


def build_sparse_matrix(
    train_agg: pl.DataFrame,
    catalog: pl.DataFrame,
) -> tuple[
    csr_matrix,
    np.ndarray,
    np.ndarray,
]:
    user_ids = (
        train_agg["user_id"]
        .unique()
        .sort()
        .to_numpy()
    )

    product_ids = (
        catalog["product_id"]
        .unique()
        .sort()
        .to_numpy()
    )

    interaction_users = (
        train_agg["user_id"]
        .to_numpy()
    )

    interaction_products = (
        train_agg["product_id"]
        .to_numpy()
    )

    values = (
        train_agg["strength"]
        .to_numpy()
        .astype(np.float32)
    )

    rows = np.searchsorted(
        user_ids,
        interaction_users,
    )

    columns = np.searchsorted(
        product_ids,
        interaction_products,
    )

    matrix = csr_matrix(
        (
            values,
            (rows, columns),
        ),
        shape=(
            len(user_ids),
            len(product_ids),
        ),
        dtype=np.float32,
    )

    matrix.sum_duplicates()

    return (
        matrix,
        user_ids,
        product_ids,
    )


def metrics_from_ranks(
    ranks: list[int | None],
    k: int,
    recommended_products: set[int],
    item_count: int,
) -> dict:
    count = len(ranks)

    hits = [
        rank
        for rank in ranks
        if rank is not None
        and rank <= k
    ]

    recall = (
        len(hits) / count
        if count
        else 0.0
    )

    ndcg = (
        sum(
            1.0
            / np.log2(rank + 1)
            for rank in hits
        )
        / count
        if count
        else 0.0
    )

    mrr = (
        sum(
            1.0 / rank
            for rank in hits
        )
        / count
        if count
        else 0.0
    )

    coverage = (
        len(recommended_products)
        / item_count
        if item_count
        else 0.0
    )

    return {
        f"recall_at_{k}": recall,
        f"hit_rate_at_{k}": recall,
        f"ndcg_at_{k}": ndcg,
        f"mrr_at_{k}": mrr,
        f"coverage_at_{k}": coverage,
        "evaluated_users": count,
        "hits": len(hits),
    }


def evaluate_popularity(
    matrix: csr_matrix,
    user_ids: np.ndarray,
    product_ids: np.ndarray,
    holdout: pl.DataFrame,
    k: int,
) -> tuple[dict, np.ndarray]:
    print(
        "\nEvaluating popularity baseline..."
    )

    popularity = np.asarray(
        matrix.sum(axis=0)
    ).ravel()

    ranking = np.argsort(
        -popularity,
        kind="stable",
    )

    ranks: list[int | None] = []

    recommended_products: set[int] = set()

    for row in holdout.iter_rows(
        named=True
    ):
        user_id = row["user_id"]

        test_product_id = row[
            "test_product_id"
        ]

        user_index = int(
            np.searchsorted(
                user_ids,
                user_id,
            )
        )

        seen = set(
            matrix.indices[
                matrix.indptr[user_index]:
                matrix.indptr[user_index + 1]
            ].tolist()
        )

        recommendations: list[int] = []

        for product_index in ranking:
            index = int(product_index)

            if index in seen:
                continue

            recommendations.append(index)

            if len(recommendations) == k:
                break

        recommended_products.update(
            recommendations
        )

        test_index = int(
            np.searchsorted(
                product_ids,
                test_product_id,
            )
        )

        try:
            rank = (
                recommendations.index(
                    test_index
                )
                + 1
            )
        except ValueError:
            rank = None

        ranks.append(rank)

    return (
        metrics_from_ranks(
            ranks=ranks,
            k=k,
            recommended_products=(
                recommended_products
            ),
            item_count=len(product_ids),
        ),
        popularity,
    )


def train_svd(
    matrix: csr_matrix,
    components: int,
    seed: int,
) -> tuple[
    TruncatedSVD,
    np.ndarray,
    np.ndarray,
]:
    print(
        "\nTraining TruncatedSVD..."
    )

    model = TruncatedSVD(
        n_components=components,
        algorithm="randomized",
        n_iter=7,
        random_state=seed,
    )

    user_factors = model.fit_transform(
        matrix
    )

    item_factors = (
        model.components_.T
        .astype(np.float32)
    )

    print(
        "Explained variance ratio: "
        f"{model.explained_variance_ratio_.sum():.4f}"
    )

    return (
        model,
        user_factors,
        item_factors,
    )


def evaluate_svd(
    matrix: csr_matrix,
    user_ids: np.ndarray,
    product_ids: np.ndarray,
    holdout: pl.DataFrame,
    user_factors: np.ndarray,
    item_factors: np.ndarray,
    k: int,
    batch_size: int,
) -> dict:
    print("\nEvaluating SVD model...")

    eval_user_ids = (
        holdout["user_id"]
        .to_numpy()
    )

    test_product_ids = (
        holdout["test_product_id"]
        .to_numpy()
    )

    eval_user_indices = (
        np.searchsorted(
            user_ids,
            eval_user_ids,
        )
    )

    test_product_indices = (
        np.searchsorted(
            product_ids,
            test_product_ids,
        )
    )

    ranks: list[int | None] = []

    recommended_products: set[int] = set()

    item_count = len(product_ids)

    actual_k = min(
        k,
        item_count,
    )

    for start in range(
        0,
        len(eval_user_indices),
        batch_size,
    ):
        end = min(
            start + batch_size,
            len(eval_user_indices),
        )

        user_batch = (
            eval_user_indices[start:end]
        )

        scores = (
            user_factors[user_batch]
            @ item_factors.T
        )

        for local_index, user_index in enumerate(
            user_batch
        ):
            seen = matrix.indices[
                matrix.indptr[user_index]:
                matrix.indptr[user_index + 1]
            ]

            scores[
                local_index,
                seen,
            ] = -np.inf

        partition_index = (
            item_count - actual_k
        )

        candidates = np.argpartition(
            scores,
            kth=partition_index,
            axis=1,
        )[:, -actual_k:]

        candidate_scores = (
            np.take_along_axis(
                scores,
                candidates,
                axis=1,
            )
        )

        ordering = np.argsort(
            -candidate_scores,
            axis=1,
        )

        top_k = np.take_along_axis(
            candidates,
            ordering,
            axis=1,
        )

        batch_test_indices = (
            test_product_indices[
                start:end
            ]
        )

        for local_index in range(
            top_k.shape[0]
        ):
            recommendations = (
                top_k[local_index]
            )

            recommended_products.update(
                int(value)
                for value
                in recommendations
            )

            test_index = int(
                batch_test_indices[
                    local_index
                ]
            )

            matches = np.flatnonzero(
                recommendations
                == test_index
            )

            if matches.size:
                ranks.append(
                    int(matches[0]) + 1
                )
            else:
                ranks.append(None)

        print(
            "  evaluated "
            f"{end:,}/"
            f"{len(eval_user_indices):,}"
        )

    return metrics_from_ranks(
        ranks=ranks,
        k=k,
        recommended_products=(
            recommended_products
        ),
        item_count=item_count,
    )


def normalize_item_embeddings(
    item_factors: np.ndarray,
) -> np.ndarray:
    norms = np.linalg.norm(
        item_factors,
        axis=1,
        keepdims=True,
    )

    norms[norms == 0] = 1.0

    return (
        item_factors
        / norms
    ).astype(np.float32)


def save_artifacts(
    artifacts_dir: Path,
    model: TruncatedSVD,
    product_ids: np.ndarray,
    item_factors: np.ndarray,
    popularity: np.ndarray,
    metrics: dict,
) -> None:
    artifacts_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    normalized_embeddings = (
        normalize_item_embeddings(
            item_factors
        )
    )

    joblib.dump(
        model,
        artifacts_dir
        / "svd_model.joblib",
    )

    np.save(
        artifacts_dir
        / "product_ids.npy",
        product_ids,
    )

    np.save(
        artifacts_dir
        / "item_factors.npy",
        item_factors,
    )

    np.save(
        artifacts_dir
        / "item_embeddings.npy",
        normalized_embeddings,
    )

    np.save(
        artifacts_dir
        / "popularity_scores.npy",
        popularity.astype(
            np.float32
        ),
    )

    with (
        artifacts_dir
        / "metrics.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metrics,
            file,
            indent=2,
        )


def main() -> None:
    args = parse_args()
    validate_args(args)

    started = perf_counter()

    print("=" * 72)
    print(
        "Dynamic Commerce Personalization"
    )
    print(
        "Offline Recommendation Training"
    )
    print("=" * 72)

    events, catalog = load_data(
        events_path=args.events,
        catalog_path=args.catalog,
    )

    evaluation_users = (
        choose_evaluation_users(
            events=events,
            max_users=(
                args.max_eval_users
            ),
            seed=args.seed,
        )
    )

    print(
        "Selected evaluation users: "
        f"{len(evaluation_users):,}"
    )

    train, holdout = (
        build_temporal_holdout(
            events=events,
            evaluation_users=(
                evaluation_users
            ),
        )
    )

    print(
        "Training events after holdout: "
        f"{train.height:,}"
    )

    train_agg = (
        aggregate_training_strength(
            train
        )
    )

    holdout = filter_valid_holdout(
        holdout=holdout,
        train_agg=train_agg,
    )

    print(
        "Valid holdout users: "
        f"{holdout.height:,}"
    )

    (
        matrix,
        user_ids,
        product_ids,
    ) = build_sparse_matrix(
        train_agg=train_agg,
        catalog=catalog,
    )

    print(
        "\nSparse interaction matrix:"
    )

    print(
        f"  users:    "
        f"{matrix.shape[0]:,}"
    )

    print(
        f"  products: "
        f"{matrix.shape[1]:,}"
    )

    print(
        f"  non-zero: "
        f"{matrix.nnz:,}"
    )

    density = (
        matrix.nnz
        / (
            matrix.shape[0]
            * matrix.shape[1]
        )
    )

    print(
        f"  density:  "
        f"{density:.8f}"
    )

    (
        popularity_metrics,
        popularity,
    ) = evaluate_popularity(
        matrix=matrix,
        user_ids=user_ids,
        product_ids=product_ids,
        holdout=holdout,
        k=args.top_k,
    )

    (
        svd_model,
        user_factors,
        item_factors,
    ) = train_svd(
        matrix=matrix,
        components=args.components,
        seed=args.seed,
    )

    svd_metrics = evaluate_svd(
        matrix=matrix,
        user_ids=user_ids,
        product_ids=product_ids,
        holdout=holdout,
        user_factors=user_factors,
        item_factors=item_factors,
        k=args.top_k,
        batch_size=args.batch_size,
    )

    elapsed = (
        perf_counter() - started
    )

    metrics = {
        "model_version": "svd-v1",
        "split": {
            "strategy": (
                "latest-item temporal holdout"
            ),
            "evaluation_users": (
                holdout.height
            ),
            "seed": args.seed,
        },
        "training": {
            "users": (
                int(matrix.shape[0])
            ),
            "products": (
                int(matrix.shape[1])
            ),
            "nonzero_interactions": (
                int(matrix.nnz)
            ),
            "components": (
                args.components
            ),
            "explained_variance_ratio": (
                float(
                    svd_model
                    .explained_variance_ratio_
                    .sum()
                )
            ),
        },
        "popularity": (
            popularity_metrics
        ),
        "svd": svd_metrics,
        "elapsed_seconds": elapsed,
    }

    save_artifacts(
        artifacts_dir=(
            args.artifacts_dir
        ),
        model=svd_model,
        product_ids=product_ids,
        item_factors=item_factors,
        popularity=popularity,
        metrics=metrics,
    )

    print("\n" + "=" * 72)
    print("RESULTS")
    print("=" * 72)

    print(
        json.dumps(
            metrics,
            indent=2,
        )
    )

    print(
        "\nArtifacts written to:"
    )

    print(
        args.artifacts_dir.resolve()
    )


if __name__ == "__main__":
    main()