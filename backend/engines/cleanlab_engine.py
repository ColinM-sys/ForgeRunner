import asyncio
import logging

import numpy as np

from backend.config import settings
from backend.schemas.score import ScoreResult
from backend.utils.text_extraction import get_scoreable_text

logger = logging.getLogger(__name__)


class CleanlabEngine:
    """Cleanlab integration for automated data quality scoring.

    Uses embedding-based issue detection: outliers, near-duplicates, quality.
    """

    name = "cleanlab"

    def __init__(self):
        self._initialized = False

    async def initialize(self) -> None:
        self._initialized = True
        logger.info("Cleanlab engine initialized")

    async def score_batch(
        self,
        examples: list[dict],
        embeddings: np.ndarray | None = None,
    ) -> list[ScoreResult]:
        """Score examples using Cleanlab's Datalab.

        Args:
            examples: List of example dicts with id, user_content, assistant_content.
            embeddings: Pre-computed embeddings from ForgeEmbedder (required).
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._score_sync, examples, embeddings)

    def _score_sync(
        self,
        examples: list[dict],
        embeddings: np.ndarray | None,
    ) -> list[ScoreResult]:
        if embeddings is None:
            logger.warning("No embeddings provided to Cleanlab. Returning default scores.")
            return [
                ScoreResult(
                    example_id=ex["id"],
                    engine_name=self.name,
                    score_type="quality",
                    score_value=0.5,
                    details="No embeddings available for scoring",
                )
                for ex in examples
            ]

        try:
            import pandas as pd
            from cleanlab import Datalab

            texts = [
                get_scoreable_text(ex["user_content"], ex["assistant_content"])
                for ex in examples
            ]

            # Create a simple dataset - use dummy labels since we're doing unsupervised
            df = pd.DataFrame({
                "text": texts,
                "label": [0] * len(texts),  # dummy labels
            })

            lab = Datalab(data=df, label_name="label")

            # Find issues using features (embeddings)
            lab.find_issues(features=embeddings)

            issues = lab.get_issues()
            results = []

            for i, ex in enumerate(examples):
                row = issues.iloc[i]

                # Overall quality score (1 = clean, 0 = problematic)
                quality_score = 1.0 - float(row.get("label_score", 0.5))
                # Invert: lower label_score means more likely mislabeled

                # Outlier score
                outlier_score = float(row.get("outlier_score", 0.5))
                is_outlier = bool(row.get("is_outlier_issue", False))

                # Near-duplicate score
                near_dup_score = float(row.get("near_duplicate_score", 1.0))
                is_near_dup = bool(row.get("is_near_duplicate_issue", False))

                # Quality score (composite)
                results.append(ScoreResult(
                    example_id=ex["id"],
                    engine_name=self.name,
                    score_type="quality",
                    score_value=max(0.0, min(1.0, outlier_score)),
                    raw_value={
                        "outlier_score": float(outlier_score),
                        "is_outlier": is_outlier,
                    },
                    details="Outlier detected" if is_outlier else "Normal",
                ))

                # Near-duplicate score
                results.append(ScoreResult(
                    example_id=ex["id"],
                    engine_name=self.name,
                    score_type="duplicate",
                    score_value=max(0.0, min(1.0, near_dup_score)),
                    raw_value={
                        "near_duplicate_score": float(near_dup_score),
                        "is_near_duplicate": is_near_dup,
                    },
                    details="Near-duplicate detected" if is_near_dup else "Unique",
                ))

            return results

        except Exception as e:
            logger.error(f"Cleanlab scoring failed: {e}")
            return [
                ScoreResult(
                    example_id=ex["id"],
                    engine_name=self.name,
                    score_type="quality",
                    score_value=0.5,
                    details=f"Scoring error: {str(e)}",
                )
                for ex in examples
            ]

    async def health_check(self) -> bool:
        return self._initialized

    async def shutdown(self) -> None:
        self._initialized = False
