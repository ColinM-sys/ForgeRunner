import asyncio
import logging
import re
from urllib.parse import urlparse

import httpx

from backend.schemas.score import ScoreResult
from backend.utils.text_extraction import get_scoreable_text

logger = logging.getLogger(__name__)

# Regex to find URLs in text
URL_PATTERN = re.compile(
    r'https?://[^\s<>"\')\]},;]+',
    re.IGNORECASE,
)


class SourceCheckerEngine:
    """Fetches URLs found in training examples and scores content against the source.

    Checks:
    - Does the example contain verifiable URLs?
    - Can the source be fetched?
    - How much overlap exists between the training content and the source?
    - Are key facts (names, numbers, dates) consistent?
    """

    name = "source_checker"

    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def initialize(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={"User-Agent": "ForgeRunner/0.1 SourceChecker"},
        )
        logger.info("SourceChecker engine initialized")

    async def score_batch(self, examples: list[dict]) -> list[ScoreResult]:
        """Score examples by checking URLs found in their content."""
        results = []
        # Process in smaller concurrent batches to avoid overwhelming
        batch_size = 10
        for i in range(0, len(examples), batch_size):
            batch = examples[i:i + batch_size]
            tasks = [self._score_one(ex) for ex in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            for ex, res in zip(batch, batch_results):
                if isinstance(res, Exception):
                    results.append(ScoreResult(
                        example_id=ex["id"],
                        engine_name=self.name,
                        score_type="source_quality",
                        score_value=0.5,
                        raw_value={"error": str(res)},
                        details="Source check failed",
                    ))
                elif res is not None:
                    results.extend(res)
                else:
                    # No URLs found - neutral score
                    results.append(ScoreResult(
                        example_id=ex["id"],
                        engine_name=self.name,
                        score_type="source_quality",
                        score_value=0.5,
                        raw_value={"urls_found": 0},
                        details="No URLs found in content",
                    ))
        return results

    async def _score_one(self, example: dict) -> list[ScoreResult] | None:
        """Score a single example by checking its URLs."""
        text = get_scoreable_text(example["user_content"], example["assistant_content"])
        urls = self._extract_urls(text)

        if not urls:
            return None

        results = []
        url_scores = []
        url_details = []

        for url in urls[:3]:  # Max 3 URLs per example
            fetch_result = await self._fetch_url(url)

            if fetch_result is None:
                url_details.append({"url": url, "status": "unreachable", "score": 0.3})
                url_scores.append(0.3)
                continue

            source_text, status_code = fetch_result

            if not source_text:
                url_details.append({"url": url, "status": f"empty ({status_code})", "score": 0.3})
                url_scores.append(0.3)
                continue

            # Compute content overlap
            overlap_score = self._compute_overlap(text, source_text)

            # Compute entity consistency (names, numbers, dates)
            entity_score = self._check_entity_consistency(text, source_text)

            # Combined source quality for this URL
            url_quality = (overlap_score * 0.6) + (entity_score * 0.4)

            url_details.append({
                "url": url,
                "status": f"fetched ({status_code})",
                "overlap": round(overlap_score, 3),
                "entity_match": round(entity_score, 3),
                "score": round(url_quality, 3),
            })
            url_scores.append(url_quality)

        # Overall source quality = average of URL scores
        avg_score = sum(url_scores) / len(url_scores) if url_scores else 0.5

        results.append(ScoreResult(
            example_id=example["id"],
            engine_name=self.name,
            score_type="source_quality",
            score_value=max(0.0, min(1.0, avg_score)),
            raw_value={
                "urls_found": len(urls),
                "urls_checked": len(url_scores),
                "url_details": url_details,
            },
            details=f"Checked {len(url_scores)} URL(s), avg quality: {avg_score:.2f}",
        ))

        # Also report if URL is reachable (basic source verification)
        reachable_count = sum(1 for d in url_details if "fetched" in d["status"])
        results.append(ScoreResult(
            example_id=example["id"],
            engine_name=self.name,
            score_type="source_reachable",
            score_value=reachable_count / len(url_details) if url_details else 0.0,
            raw_value={"reachable": reachable_count, "total": len(url_details)},
            details=f"{reachable_count}/{len(url_details)} URLs reachable",
        ))

        return results

    def _extract_urls(self, text: str) -> list[str]:
        """Extract unique URLs from text."""
        urls = URL_PATTERN.findall(text)
        # Clean trailing punctuation
        cleaned = []
        seen = set()
        for url in urls:
            url = url.rstrip('.,;:!?)\'"]')
            if url not in seen and self._is_valid_url(url):
                cleaned.append(url)
                seen.add(url)
        return cleaned

    def _is_valid_url(self, url: str) -> bool:
        """Basic URL validation."""
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc and '.' in parsed.netloc)
        except Exception:
            return False

    async def _fetch_url(self, url: str) -> tuple[str, int] | None:
        """Fetch URL content. Returns (text, status_code) or None."""
        try:
            resp = await self._client.get(url)
            if resp.status_code >= 400:
                return None

            content_type = resp.headers.get("content-type", "")
            if "text/html" in content_type:
                # Strip HTML tags for comparison
                text = self._strip_html(resp.text)
            else:
                text = resp.text

            # Limit to first 10K chars
            return text[:10000], resp.status_code
        except Exception as e:
            logger.debug(f"Failed to fetch {url}: {e}")
            return None

    def _strip_html(self, html: str) -> str:
        """Basic HTML tag stripping."""
        # Remove script and style blocks
        html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
        # Remove tags
        text = re.sub(r'<[^>]+>', ' ', html)
        # Collapse whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _compute_overlap(self, training_text: str, source_text: str) -> float:
        """Compute word-level overlap between training content and source.

        Higher = more of the training content is grounded in the source.
        """
        training_words = set(training_text.lower().split())
        source_words = set(source_text.lower().split())

        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'shall', 'to', 'of', 'in', 'for',
            'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during',
            'and', 'but', 'or', 'nor', 'not', 'so', 'yet', 'both', 'either',
            'neither', 'this', 'that', 'these', 'those', 'it', 'its',
        }
        training_words -= stop_words
        source_words -= stop_words

        if not training_words:
            return 0.5

        overlap = training_words & source_words
        return len(overlap) / len(training_words)

    def _check_entity_consistency(self, training_text: str, source_text: str) -> float:
        """Check if named entities (numbers, dates, proper nouns) in training match source."""
        # Extract numbers
        training_numbers = set(re.findall(r'\$[\d,.]+|\d{1,3}(?:,\d{3})*(?:\.\d+)?%?', training_text))
        source_numbers = set(re.findall(r'\$[\d,.]+|\d{1,3}(?:,\d{3})*(?:\.\d+)?%?', source_text))

        # Extract capitalized phrases (likely proper nouns / company names)
        training_entities = set(re.findall(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', training_text))
        source_entities = set(re.findall(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', source_text))

        # Extract dates
        training_dates = set(re.findall(
            r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s*\d{4}',
            training_text,
        ))
        source_dates = set(re.findall(
            r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s*\d{4}',
            source_text,
        ))

        scores = []

        if training_numbers:
            match_rate = len(training_numbers & source_numbers) / len(training_numbers)
            scores.append(match_rate)

        if training_entities:
            # Only check entities with 2+ chars to avoid noise
            sig_entities = {e for e in training_entities if len(e) > 3}
            sig_source = {e for e in source_entities if len(e) > 3}
            if sig_entities:
                match_rate = len(sig_entities & sig_source) / len(sig_entities)
                scores.append(match_rate)

        if training_dates:
            match_rate = len(training_dates & source_dates) / len(training_dates)
            scores.append(match_rate)

        if not scores:
            return 0.5  # No entities to check

        return sum(scores) / len(scores)

    async def health_check(self) -> bool:
        return self._client is not None

    async def shutdown(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
