import asyncio
import hashlib
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

import httpx
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.models.bucket import Bucket
from backend.models.dataset import Dataset, DatasetStatus
from backend.models.example import Example

logger = logging.getLogger(__name__)

router = APIRouter()

URL_PATTERN = re.compile(r'https?://[^\s<>"\')\]},;]+', re.IGNORECASE)


class SourceCheckRequest(BaseModel):
    urls: list[str]  # Can be raw URLs or text with URLs mixed in


class SourceResult(BaseModel):
    url: str
    reachable: bool
    status_code: int | None
    title: str | None
    word_count: int
    content_preview: str
    scores: dict
    overall_score: float
    details: str


class SourceCheckResponse(BaseModel):
    results: list[SourceResult]
    total_checked: int
    avg_score: float
    checked_at: str


def extract_urls_from_text(text: str) -> list[str]:
    """Extract all URLs from a block of text (handles mixed text + URLs)."""
    urls = URL_PATTERN.findall(text)
    cleaned = []
    seen = set()
    for url in urls:
        url = url.rstrip('.,;:!?)\'"]')
        if url not in seen and '.' in url:
            cleaned.append(url)
            seen.add(url)
    return cleaned


def extract_all_urls(inputs: list[str]) -> list[str]:
    """Extract URLs from a list that may contain raw URLs, text with URLs, or newline-separated URLs."""
    all_urls = []
    seen = set()
    for item in inputs:
        # Split by newlines in case someone pastes a block
        for line in item.split('\n'):
            line = line.strip()
            if not line:
                continue
            # Check if the whole line is a URL
            if line.startswith('http://') or line.startswith('https://'):
                url = line.rstrip('.,;:!?)\'"]')
                if url not in seen:
                    all_urls.append(url)
                    seen.add(url)
            else:
                # Extract URLs from mixed text
                for url in extract_urls_from_text(line):
                    if url not in seen:
                        all_urls.append(url)
                        seen.add(url)
    return all_urls


def strip_html(html: str) -> str:
    """Strip HTML to plain text."""
    html = re.sub(r'<(script|style|noscript)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_title(html: str) -> str | None:
    """Extract <title> from HTML."""
    match = re.search(r'<title[^>]*>(.*?)</title>', html, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else None


def score_content_quality(text: str) -> dict:
    """Score the quality of fetched content."""
    scores = {}

    words = text.split()
    word_count = len(words)

    # Length score: prefer substantial content
    if word_count >= 500:
        scores['length'] = 1.0
    elif word_count >= 200:
        scores['length'] = 0.8
    elif word_count >= 50:
        scores['length'] = 0.5
    else:
        scores['length'] = 0.2

    # Readability: average word length (good range: 4-7 chars)
    if words:
        avg_word_len = sum(len(w) for w in words) / len(words)
        if 4 <= avg_word_len <= 7:
            scores['readability'] = 0.9
        elif 3 <= avg_word_len <= 9:
            scores['readability'] = 0.6
        else:
            scores['readability'] = 0.3
    else:
        scores['readability'] = 0.0

    # Structure: presence of sentences (periods, question marks)
    sentence_count = len(re.findall(r'[.!?]+', text))
    if sentence_count >= 10:
        scores['structure'] = 1.0
    elif sentence_count >= 3:
        scores['structure'] = 0.7
    else:
        scores['structure'] = 0.3

    # Information density: ratio of unique words (higher = more diverse content)
    if words:
        unique_ratio = len(set(w.lower() for w in words)) / len(words)
        scores['info_density'] = min(1.0, unique_ratio * 1.5)  # Scale up, cap at 1.0
    else:
        scores['info_density'] = 0.0

    # Entity richness: proper nouns, numbers, dates
    entities = len(re.findall(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', text))
    numbers = len(re.findall(r'\$?[\d,.]+%?', text))
    entity_score = min(1.0, (entities + numbers) / max(word_count * 0.1, 1))
    scores['entity_richness'] = entity_score

    return scores


async def check_single_url(client: httpx.AsyncClient, url: str) -> SourceResult:
    """Fetch and score a single URL."""
    try:
        resp = await client.get(url)
        status_code = resp.status_code

        if status_code >= 400:
            return SourceResult(
                url=url,
                reachable=False,
                status_code=status_code,
                title=None,
                word_count=0,
                content_preview="",
                scores={},
                overall_score=0.0,
                details=f"HTTP {status_code} error",
            )

        content_type = resp.headers.get("content-type", "")
        raw_html = resp.text
        title = extract_title(raw_html) if "text/html" in content_type else None
        text = strip_html(raw_html) if "text/html" in content_type else raw_html
        text = text[:20000]  # Cap at 20K chars

        word_count = len(text.split())
        preview = text[:300].strip()
        if len(text) > 300:
            preview += "..."

        scores = score_content_quality(text)

        # Weighted overall
        overall = (
            scores.get('length', 0) * 0.25 +
            scores.get('readability', 0) * 0.15 +
            scores.get('structure', 0) * 0.20 +
            scores.get('info_density', 0) * 0.20 +
            scores.get('entity_richness', 0) * 0.20
        )

        return SourceResult(
            url=url,
            reachable=True,
            status_code=status_code,
            title=title,
            word_count=word_count,
            content_preview=preview,
            scores=scores,
            overall_score=round(overall, 3),
            details=f"{word_count} words, {len(scores)} quality signals",
        )

    except httpx.TimeoutException:
        return SourceResult(
            url=url, reachable=False, status_code=None, title=None,
            word_count=0, content_preview="", scores={},
            overall_score=0.0, details="Request timed out",
        )
    except Exception as e:
        return SourceResult(
            url=url, reachable=False, status_code=None, title=None,
            word_count=0, content_preview="", scores={},
            overall_score=0.0, details=f"Error: {str(e)[:100]}",
        )


@router.post("/check", response_model=SourceCheckResponse)
async def check_sources(request: SourceCheckRequest):
    """Check a list of URLs for content quality.

    Accepts raw URLs, text with URLs mixed in, or newline-separated URLs.
    Each URL is fetched and scored individually.
    """
    urls = extract_all_urls(request.urls)

    if not urls:
        raise HTTPException(status_code=400, detail="No valid URLs found in input")

    if len(urls) > 50:
        raise HTTPException(status_code=400, detail=f"Too many URLs ({len(urls)}). Max 50 at a time.")

    async with httpx.AsyncClient(
        timeout=15.0,
        follow_redirects=True,
        headers={"User-Agent": "ForgeRunner/0.1 SourceChecker"},
    ) as client:
        # Check URLs concurrently in batches of 10
        results = []
        for i in range(0, len(urls), 10):
            batch = urls[i:i + 10]
            batch_results = await asyncio.gather(
                *[check_single_url(client, url) for url in batch]
            )
            results.extend(batch_results)

    scored_results = [r for r in results if r.overall_score > 0]
    avg = sum(r.overall_score for r in scored_results) / len(scored_results) if scored_results else 0.0

    return SourceCheckResponse(
        results=results,
        total_checked=len(results),
        avg_score=round(avg, 3),
        checked_at=datetime.now(timezone.utc).isoformat(),
    )


# ── Gap Analysis ──────────────────────────────────────────────────────

# Module-level reference, set by main.py at startup
embedder = None


class GapAnalysisRequest(BaseModel):
    urls: list[str]
    dataset_id: str


class GapSourceResult(BaseModel):
    url: str
    reachable: bool
    title: str | None
    word_count: int
    content_preview: str
    content_quality: float  # from quick-check scoring
    novelty_score: float  # 0=redundant, 1=totally novel
    closest_bucket: str | None
    closest_bucket_color: str | None
    bucket_coverage: float  # how well-covered that bucket already is (0-1)
    closest_examples: list[dict]  # top 3 most similar existing examples
    recommendation: str  # "high_value" | "moderate_value" | "low_value" | "redundant"
    recommendation_reason: str
    details: str


class BucketStats(BaseModel):
    name: str
    display_name: str
    color: str
    count: int
    avg_score: float


class GapAnalysisResponse(BaseModel):
    results: list[GapSourceResult]
    dataset_name: str
    dataset_size: int
    bucket_breakdown: list[BucketStats]
    analyzed_at: str


async def _fetch_url_text(client: httpx.AsyncClient, url: str) -> tuple[str, bool, str | None, int, str]:
    """Fetch a URL and return (text, reachable, title, word_count, preview)."""
    try:
        resp = await client.get(url)
        if resp.status_code >= 400:
            return "", False, None, 0, ""

        content_type = resp.headers.get("content-type", "")
        raw_html = resp.text
        title = extract_title(raw_html) if "text/html" in content_type else None
        text = strip_html(raw_html) if "text/html" in content_type else raw_html
        text = text[:20000]

        word_count = len(text.split())
        preview = text[:300].strip()
        if len(text) > 300:
            preview += "..."

        return text, True, title, word_count, preview
    except Exception:
        return "", False, None, 0, ""


@router.post("/gap-analysis", response_model=GapAnalysisResponse)
async def gap_analysis(request: GapAnalysisRequest, db: AsyncSession = Depends(get_db)):
    """Compare source URLs against an existing dataset to find gaps.

    Embeds fetched content using the same model as the dataset, then compares
    against cached dataset embeddings to determine novelty, bucket fit, and value.
    """
    if embedder is None:
        raise HTTPException(status_code=503, detail="Embedding engine not initialized. Score a dataset first.")

    # Validate dataset exists and is scored
    ds_result = await db.execute(select(Dataset).where(Dataset.id == request.dataset_id))
    dataset = ds_result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    if dataset.status != DatasetStatus.scored:
        raise HTTPException(status_code=400, detail="Dataset must be scored first before gap analysis")

    # Extract URLs
    urls = extract_all_urls(request.urls)
    if not urls:
        raise HTTPException(status_code=400, detail="No valid URLs found in input")
    if len(urls) > 20:
        raise HTTPException(status_code=400, detail=f"Too many URLs ({len(urls)}). Max 20 for gap analysis.")

    # Load dataset embeddings from cache
    cache_key = hashlib.md5(
        f"{settings.EMBEDDING_MODEL}_{dataset.total_examples}".encode()
    ).hexdigest()
    cache_path = Path(settings.EMBEDDING_CACHE_DIR) / f"{cache_key}.npy"
    if not cache_path.exists():
        raise HTTPException(status_code=400, detail="Dataset embeddings not found. Re-run scoring first.")

    dataset_embeddings = np.load(str(cache_path))

    # Load examples for closest-match lookup (id, user_content preview, bucket)
    ex_result = await db.execute(
        select(Example).where(Example.dataset_id == request.dataset_id).order_by(Example.line_number)
    )
    examples = ex_result.scalars().all()
    example_texts = [
        (ex.user_content or "")[:120] for ex in examples
    ]
    example_ids = [ex.id for ex in examples]

    # Load buckets
    bucket_result = await db.execute(select(Bucket))
    buckets = {b.id: b for b in bucket_result.scalars().all()}

    # Build bucket stats
    bucket_counts: dict[str, int] = {}
    bucket_score_sums: dict[str, float] = {}
    for ex in examples:
        bid = ex.bucket_id
        if bid:
            bucket_counts[bid] = bucket_counts.get(bid, 0) + 1
            bucket_score_sums[bid] = bucket_score_sums.get(bid, 0) + (ex.aggregate_score or 0)

    bucket_stats_list = []
    for bid, b in buckets.items():
        cnt = bucket_counts.get(bid, 0)
        avg = bucket_score_sums.get(bid, 0) / cnt if cnt > 0 else 0
        bucket_stats_list.append(BucketStats(
            name=b.name, display_name=b.display_name, color=b.color,
            count=cnt, avg_score=round(avg, 3),
        ))
    bucket_stats_list.sort(key=lambda x: x.count, reverse=True)

    # Build a mapping from bucket keywords to bucket for source classification
    from backend.services.bucketing import DEFAULT_BUCKETS
    bucket_id_by_name = {b.name: b.id for b in buckets.values()}

    # Fetch all URLs
    async with httpx.AsyncClient(
        timeout=15.0, follow_redirects=True,
        headers={"User-Agent": "ForgeRunner/0.1 GapAnalysis"},
    ) as client:
        fetch_tasks = [_fetch_url_text(client, url) for url in urls]
        fetched = await asyncio.gather(*fetch_tasks)

    # Embed fetched content
    source_texts = []
    source_indices = []  # indices of reachable URLs
    for i, (text, reachable, _, _, _) in enumerate(fetched):
        if reachable and text.strip():
            source_texts.append(text[:5000])  # Cap for embedding
            source_indices.append(i)

    source_embeddings = None
    if source_texts:
        source_embeddings = await embedder.embed_texts_async(source_texts)

    # Compare each source against dataset
    results = []
    embed_idx = 0
    total_examples = len(examples)

    for i, url in enumerate(urls):
        text, reachable, title, word_count, preview = fetched[i]

        if not reachable or not text.strip():
            results.append(GapSourceResult(
                url=url, reachable=False, title=title, word_count=word_count,
                content_preview=preview, content_quality=0, novelty_score=0,
                closest_bucket=None, closest_bucket_color=None, bucket_coverage=0,
                closest_examples=[], recommendation="low_value",
                recommendation_reason="Could not fetch content from this URL",
                details="Unreachable",
            ))
            continue

        # Content quality from quick-check scorer
        quality_scores = score_content_quality(text)
        content_quality = (
            quality_scores.get('length', 0) * 0.25 +
            quality_scores.get('readability', 0) * 0.15 +
            quality_scores.get('structure', 0) * 0.20 +
            quality_scores.get('info_density', 0) * 0.20 +
            quality_scores.get('entity_richness', 0) * 0.20
        )

        # Get this source's embedding
        if i in source_indices and source_embeddings is not None:
            src_emb = source_embeddings[source_indices.index(i)]

            # Cosine similarity against all dataset embeddings (already normalized)
            similarities = dataset_embeddings @ src_emb

            # Novelty: inverse of max similarity to existing data
            max_sim = float(np.max(similarities))
            avg_top10_sim = float(np.mean(np.partition(similarities, -min(10, len(similarities)))[-min(10, len(similarities)):]))
            novelty = 1.0 - avg_top10_sim  # High novelty = different from existing

            # Find closest examples
            top_indices = np.argsort(similarities)[-3:][::-1]
            closest = []
            for idx in top_indices:
                ex = examples[idx]
                bucket_name = buckets[ex.bucket_id].display_name if ex.bucket_id and ex.bucket_id in buckets else "Unknown"
                closest.append({
                    "preview": example_texts[idx],
                    "similarity": round(float(similarities[idx]), 3),
                    "bucket": bucket_name,
                    "score": round(ex.aggregate_score, 3) if ex.aggregate_score else 0,
                })

            # Determine best-fit bucket by finding which bucket's examples are most similar
            bucket_similarities: dict[str, list[float]] = {}
            for idx in range(len(examples)):
                bid = examples[idx].bucket_id
                if bid:
                    if bid not in bucket_similarities:
                        bucket_similarities[bid] = []
                    bucket_similarities[bid].append(float(similarities[idx]))

            best_bucket_id = None
            best_bucket_avg_sim = 0
            for bid, sims in bucket_similarities.items():
                top_sims = sorted(sims, reverse=True)[:10]
                avg_sim = sum(top_sims) / len(top_sims) if top_sims else 0
                if avg_sim > best_bucket_avg_sim:
                    best_bucket_avg_sim = avg_sim
                    best_bucket_id = bid

            closest_bucket_name = None
            closest_bucket_color = None
            bucket_coverage = 0.0
            if best_bucket_id and best_bucket_id in buckets:
                closest_bucket_name = buckets[best_bucket_id].display_name
                closest_bucket_color = buckets[best_bucket_id].color
                bucket_coverage = bucket_counts.get(best_bucket_id, 0) / total_examples if total_examples > 0 else 0

            # Recommendation logic
            if content_quality < 0.3:
                recommendation = "low_value"
                reason = "Content quality is too low to be useful training data"
            elif novelty < 0.15:
                recommendation = "redundant"
                reason = f"Very similar to existing data (top match: {max_sim:.0%} similar)"
            elif novelty < 0.30 and bucket_coverage > 0.3:
                recommendation = "low_value"
                reason = f"Similar to existing data and bucket '{closest_bucket_name}' is already well-covered ({bucket_coverage:.0%})"
            elif novelty >= 0.5:
                recommendation = "high_value"
                reason = f"Highly novel content (novelty: {novelty:.0%}), would add new patterns to the dataset"
            elif novelty >= 0.30 and bucket_coverage < 0.1:
                recommendation = "high_value"
                reason = f"Novel content for underrepresented bucket '{closest_bucket_name}' ({bucket_coverage:.0%} coverage)"
            else:
                recommendation = "moderate_value"
                reason = f"Moderately novel (novelty: {novelty:.0%}), would add some variety"

            results.append(GapSourceResult(
                url=url, reachable=True, title=title, word_count=word_count,
                content_preview=preview, content_quality=round(content_quality, 3),
                novelty_score=round(novelty, 3),
                closest_bucket=closest_bucket_name, closest_bucket_color=closest_bucket_color,
                bucket_coverage=round(bucket_coverage, 3),
                closest_examples=closest,
                recommendation=recommendation, recommendation_reason=reason,
                details=f"Novelty: {novelty:.0%}, Quality: {content_quality:.0%}, Best bucket: {closest_bucket_name}",
            ))
        else:
            results.append(GapSourceResult(
                url=url, reachable=True, title=title, word_count=word_count,
                content_preview=preview, content_quality=round(content_quality, 3),
                novelty_score=0, closest_bucket=None, closest_bucket_color=None,
                bucket_coverage=0, closest_examples=[],
                recommendation="low_value",
                recommendation_reason="Could not embed content for comparison",
                details="Embedding failed",
            ))

    return GapAnalysisResponse(
        results=results,
        dataset_name=dataset.name,
        dataset_size=dataset.total_examples,
        bucket_breakdown=bucket_stats_list,
        analyzed_at=datetime.now(timezone.utc).isoformat(),
    )
