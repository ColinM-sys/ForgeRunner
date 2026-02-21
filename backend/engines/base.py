from typing import Protocol

from backend.schemas.score import ScoreResult


class ScoringEngine(Protocol):
    """Protocol that all scoring engines must implement."""

    name: str

    async def initialize(self) -> None:
        """Connect to external service or load model."""
        ...

    async def score_batch(
        self,
        examples: list[dict],
    ) -> list[ScoreResult]:
        """Score a batch of examples.

        Each example dict has: id, system_prompt, user_content, assistant_content.
        Returns one or more ScoreResult per example.
        """
        ...

    async def health_check(self) -> bool:
        """Verify engine is operational."""
        ...

    async def shutdown(self) -> None:
        """Clean up resources."""
        ...
