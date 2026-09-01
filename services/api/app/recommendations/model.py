from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from app.core.config import settings


@dataclass
class RankedCandidate:
    product_id: int
    score: float
    reason: str


class RecommendationModel:
    MODEL_VERSION = "session-svd-v2"

    def __init__(
        self,
        artifacts_dir: Path,
    ) -> None:
        self.product_ids = np.load(
            artifacts_dir
            / "product_ids.npy"
        )

        # IMPORTANT:
        # Use the RAW TruncatedSVD item factors.
        #
        # These correspond to components_.T from training
        # and preserve the magnitude information used by
        # the offline reconstruction model.
        self.item_factors = np.load(
            artifacts_dir
            / "item_factors.npy"
        ).astype(
            np.float32
        )

        raw_popularity = np.load(
            artifacts_dir
            / "popularity_scores.npy"
        ).astype(
            np.float32
        )

        if (
            len(self.product_ids)
            != self.item_factors.shape[0]
        ):
            raise ValueError(
                "Product ID and item-factor "
                "artifact sizes do not match."
            )

        self.product_to_index = {
            int(product_id): index
            for index, product_id
            in enumerate(
                self.product_ids
            )
        }

        self.popularity = (
            self._normalize_popularity(
                raw_popularity
            )
        )

    @staticmethod
    def _normalize_popularity(
        popularity: np.ndarray,
    ) -> np.ndarray:
        transformed = np.log1p(
            np.maximum(
                popularity,
                0.0,
            )
        )

        minimum = float(
            transformed.min()
        )

        maximum = float(
            transformed.max()
        )

        denominator = (
            maximum - minimum
        )

        if denominator <= 0:
            return np.zeros_like(
                transformed,
                dtype=np.float32,
            )

        return (
            (
                transformed
                - minimum
            )
            / denominator
        ).astype(
            np.float32
        )

    @staticmethod
    def _normalize_scores(
        scores: np.ndarray,
    ) -> np.ndarray:
        finite = np.isfinite(
            scores
        )

        normalized = np.zeros_like(
            scores,
            dtype=np.float32,
        )

        if not finite.any():
            return normalized

        finite_scores = scores[
            finite
        ]

        minimum = float(
            finite_scores.min()
        )

        maximum = float(
            finite_scores.max()
        )

        denominator = (
            maximum - minimum
        )

        if denominator <= 0:
            return normalized

        normalized[finite] = (
            (
                finite_scores
                - minimum
            )
            / denominator
        )

        return normalized

    def build_session_factor(
        self,
        product_weights: dict[int, float],
    ) -> np.ndarray | None:
        """
        Project live session interactions into the
        same latent space used during offline SVD
        evaluation.

        Training used log1p aggregated implicit
        interaction strengths, so the online session
        applies the same compression.
        """

        session_factor = np.zeros(
            self.item_factors.shape[1],
            dtype=np.float32,
        )

        valid_signal = False

        for (
            product_id,
            raw_weight,
        ) in product_weights.items():
            index = (
                self.product_to_index.get(
                    product_id
                )
            )

            if index is None:
                continue

            if raw_weight <= 0:
                continue

            strength = np.log1p(
                raw_weight
            )

            session_factor += (
                float(strength)
                * self.item_factors[
                    index
                ]
            )

            valid_signal = True

        if not valid_signal:
            return None

        if not np.any(
            session_factor
        ):
            return None

        return session_factor

    def recommend(
        self,
        product_weights: dict[int, float],
        limit: int,
    ) -> tuple[
        str,
        list[RankedCandidate],
    ]:
        session_factor = (
            self.build_session_factor(
                product_weights
            )
        )

        seen_product_ids = set(
            product_weights
        )

        if session_factor is None:
            strategy = "popularity"

            scores = (
                self.popularity.copy()
            )

            reason = (
                "Popular with shoppers"
            )

        else:
            strategy = "session_intent"

            # Same reconstruction geometry used by
            # the offline SVD model:
            #
            # session latent factor
            #       @
            # item latent factors.T
            #
            latent_scores = (
                self.item_factors
                @ session_factor
            )

            latent_scores = (
                self._normalize_scores(
                    latent_scores
                )
            )

            # Keep popularity only as a small prior.
            #
            # Personalization remains dominant.
            scores = (
                0.95
                * latent_scores
                +
                0.05
                * self.popularity
            )

            reason = (
                "Based on your current "
                "session intent"
            )

        for product_id in (
            seen_product_ids
        ):
            index = (
                self.product_to_index.get(
                    product_id
                )
            )

            if index is not None:
                scores[index] = -np.inf

        valid_count = int(
            np.isfinite(
                scores
            ).sum()
        )

        actual_limit = min(
            limit,
            valid_count,
        )

        if actual_limit <= 0:
            return (
                strategy,
                [],
            )

        candidate_indices = (
            np.argpartition(
                scores,
                -actual_limit,
            )[
                -actual_limit:
            ]
        )

        candidate_indices = (
            candidate_indices[
                np.argsort(
                    -scores[
                        candidate_indices
                    ]
                )
            ]
        )

        results = []

        for index in candidate_indices:
            results.append(
                RankedCandidate(
                    product_id=int(
                        self.product_ids[
                            index
                        ]
                    ),
                    score=float(
                        scores[index]
                    ),
                    reason=reason,
                )
            )

        return (
            strategy,
            results,
        )


@lru_cache
def get_recommendation_model(
) -> RecommendationModel:
    return RecommendationModel(
        artifacts_dir=(
            settings.model_artifacts_dir
        )
    )