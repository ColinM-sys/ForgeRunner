import asyncio
import hashlib
import json
import logging
from pathlib import Path

import numpy as np

from backend.config import settings
from backend.schemas.score import ScoreResult
from backend.utils.text_extraction import get_scoreable_text

logger = logging.getLogger(__name__)


class ForgeEmbedderEngine:
    """Custom embedding + clustering engine replacing Lilac.

    Uses sentence-transformers for embeddings and BERTopic for clustering.
    """

    name = "forge_embedder"

    def __init__(self):
        self.model = None
        self.topic_model = None
        self._cache_dir = Path(settings.EMBEDDING_CACHE_DIR)

    async def initialize(self) -> None:
        """Load embedding model and BERTopic."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._load_models)

    def _load_models(self):
        from sentence_transformers import SentenceTransformer

        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        self.model = SentenceTransformer(
            settings.EMBEDDING_MODEL,
            device=settings.EMBEDDING_DEVICE,
        )
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info("ForgeEmbedder initialized")

    async def score_batch(self, examples: list[dict]) -> list[ScoreResult]:
        """Compute embeddings, cluster, and score examples."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._score_batch_sync, examples)

    def _score_batch_sync(self, examples: list[dict]) -> list[ScoreResult]:
        texts = [
            get_scoreable_text(ex["user_content"], ex["assistant_content"])
            for ex in examples
        ]
        ids = [ex["id"] for ex in examples]

        # Compute embeddings
        embeddings = self._get_or_compute_embeddings(ids, texts)

        # Cluster with BERTopic
        topics, cluster_scores = self._cluster(texts, embeddings)

        # Compute similarity scores (cosine similarity to cluster centroid)
        results = []
        for i, ex in enumerate(examples):
            # Cluster assignment
            results.append(ScoreResult(
                example_id=ex["id"],
                engine_name=self.name,
                score_type="cluster",
                score_value=max(0.0, min(1.0, cluster_scores[i])) if cluster_scores[i] is not None else 0.5,
                raw_value={"topic_id": int(topics[i]), "topic_label": str(topics[i])},
                details=f"Assigned to topic {topics[i]}",
            ))

            # Similarity to nearest neighbors (quality indicator)
            similarity = self._compute_nn_similarity(embeddings, i)
            results.append(ScoreResult(
                example_id=ex["id"],
                engine_name=self.name,
                score_type="similarity",
                score_value=similarity,
                raw_value={"nn_similarity": float(similarity)},
                details=f"Avg similarity to 5 nearest neighbors: {similarity:.3f}",
            ))

        return results

    def _get_or_compute_embeddings(self, ids: list[str], texts: list[str]) -> np.ndarray:
        """Get cached embeddings or compute new ones."""
        cache_key = hashlib.md5(
            f"{settings.EMBEDDING_MODEL}_{len(ids)}".encode()
        ).hexdigest()
        cache_path = self._cache_dir / f"{cache_key}.npy"

        if cache_path.exists():
            logger.info(f"Loading cached embeddings from {cache_path}")
            return np.load(str(cache_path))

        logger.info(f"Computing embeddings for {len(texts)} examples...")
        embeddings = self.model.encode(
            texts,
            show_progress_bar=True,
            batch_size=settings.SCORING_BATCH_SIZE,
            normalize_embeddings=True,
        )

        np.save(str(cache_path), embeddings)
        logger.info(f"Cached embeddings to {cache_path}")
        return embeddings

    def _cluster(self, texts: list[str], embeddings: np.ndarray) -> tuple[list[int], list[float | None]]:
        """Cluster examples using BERTopic."""
        if len(texts) < 10:
            return [0] * len(texts), [0.5] * len(texts)

        try:
            from bertopic import BERTopic
            from sklearn.cluster import MiniBatchKMeans
            from umap import UMAP

            umap_model = UMAP(n_components=5, n_neighbors=15, min_dist=0.0, metric="cosine", random_state=42)
            cluster_model = MiniBatchKMeans(n_clusters=min(20, len(texts) // 10), random_state=42)

            self.topic_model = BERTopic(
                umap_model=umap_model,
                hdbscan_model=cluster_model,
                calculate_probabilities=True,
                verbose=False,
            )

            topics, probs = self.topic_model.fit_transform(texts, embeddings)

            # Convert probabilities to confidence scores
            if probs is not None and len(probs.shape) > 1:
                scores = [float(np.max(p)) for p in probs]
            else:
                scores = [0.5] * len(texts)

            return list(topics), scores

        except Exception as e:
            logger.warning(f"BERTopic clustering failed: {e}. Falling back to no clustering.")
            return [0] * len(texts), [0.5] * len(texts)

    def _compute_nn_similarity(self, embeddings: np.ndarray, index: int, k: int = 5) -> float:
        """Compute average cosine similarity to k nearest neighbors."""
        if len(embeddings) <= k:
            return 0.5

        # Cosine similarity (embeddings are already normalized)
        similarities = embeddings @ embeddings[index]
        similarities[index] = -1  # Exclude self
        top_k = np.partition(similarities, -k)[-k:]
        return float(np.mean(top_k))

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Embed arbitrary texts (for gap analysis, etc.)."""
        if self.model is None:
            raise RuntimeError("ForgeEmbedder not initialized")
        return self.model.encode(
            texts,
            show_progress_bar=False,
            batch_size=settings.SCORING_BATCH_SIZE,
            normalize_embeddings=True,
        )

    async def embed_texts_async(self, texts: list[str]) -> np.ndarray:
        """Async wrapper for embed_texts."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed_texts, texts)

    def get_cached_embeddings_path(self, example_count: int) -> Path | None:
        """Get the path to cached embeddings for a dataset of given size."""
        cache_key = hashlib.md5(
            f"{settings.EMBEDDING_MODEL}_{example_count}".encode()
        ).hexdigest()
        cache_path = self._cache_dir / f"{cache_key}.npy"
        return cache_path if cache_path.exists() else None

    async def health_check(self) -> bool:
        return self.model is not None

    async def shutdown(self) -> None:
        self.model = None
        self.topic_model = None
