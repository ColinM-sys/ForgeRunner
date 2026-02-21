import json
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.bucket import Bucket
from backend.models.example import Example

# Default system buckets
DEFAULT_BUCKETS = [
    {
        "name": "press_release",
        "display_name": "Press Release",
        "description": "Press release drafts, templates, and examples",
        "color": "#3B82F6",
        "detection_rules": {
            "keywords": ["press release", "PRNewswire", "media contact", "for immediate release", "news release"],
            "system_prompt_patterns": [],
        },
    },
    {
        "name": "crisis_comms",
        "display_name": "Crisis Communications",
        "description": "Crisis management, incident response, reputation management",
        "color": "#EF4444",
        "detection_rules": {
            "keywords": ["crisis", "incident response", "reputation management", "crisis communication",
                         "damage control", "crisis plan"],
            "system_prompt_patterns": [],
        },
    },
    {
        "name": "social_media",
        "display_name": "Social Media",
        "description": "Social media strategy, posts, engagement",
        "color": "#8B5CF6",
        "detection_rules": {
            "keywords": ["social media", "twitter", "linkedin", "instagram", "engagement rate",
                         "followers", "hashtag"],
            "system_prompt_patterns": [],
        },
    },
    {
        "name": "general_marketing",
        "display_name": "General Marketing",
        "description": "Marketing strategy, branding, campaigns",
        "color": "#10B981",
        "detection_rules": {
            "keywords": ["marketing strategy", "brand", "campaign", "target audience", "market research",
                         "competitive analysis"],
            "system_prompt_patterns": [],
        },
    },
    {
        "name": "knowledge",
        "display_name": "Knowledge",
        "description": "Domain knowledge, factual Q&A, business advisory",
        "color": "#F59E0B",
        "detection_rules": {
            "keywords": [],
            "system_prompt_patterns": [],
        },
    },
    {
        "name": "workflow_intake",
        "display_name": "Workflow / Intake",
        "description": "Multi-turn workflow conversations, PRrunner intake",
        "color": "#06B6D4",
        "detection_rules": {
            "keywords": [],
            "system_prompt_patterns": ["PRrunner", "workflow", "intake"],
        },
    },
    {
        "name": "uncategorized",
        "display_name": "Uncategorized",
        "description": "Not yet categorized - needs manual review",
        "color": "#6B7280",
        "detection_rules": {"keywords": [], "system_prompt_patterns": []},
    },
]


async def ensure_default_buckets(db: AsyncSession) -> dict[str, str]:
    """Create default buckets if they don't exist. Returns name -> id mapping."""
    bucket_map = {}
    for bucket_def in DEFAULT_BUCKETS:
        result = await db.execute(select(Bucket).where(Bucket.name == bucket_def["name"]))
        bucket = result.scalar_one_or_none()
        if not bucket:
            bucket = Bucket(
                name=bucket_def["name"],
                display_name=bucket_def["display_name"],
                description=bucket_def["description"],
                color=bucket_def["color"],
                is_system=True,
                detection_rules=json.dumps(bucket_def["detection_rules"]),
            )
            db.add(bucket)
            await db.flush()
        bucket_map[bucket.name] = bucket.id
    await db.commit()
    return bucket_map


def classify_example(example: Example, bucket_map: dict[str, str]) -> str | None:
    """Classify an example into a bucket using rule-based and keyword matching.

    Returns bucket_id or None if uncategorized.
    """
    text_to_search = f"{example.user_content} {example.assistant_content}".lower()
    system_prompt = example.system_prompt.lower()

    # 1. System prompt pattern matching (highest priority)
    for bucket_def in DEFAULT_BUCKETS:
        rules = bucket_def["detection_rules"]
        for pattern in rules.get("system_prompt_patterns", []):
            if pattern.lower() in system_prompt:
                return bucket_map.get(bucket_def["name"])

    # 2. Keyword matching in content
    best_match = None
    best_score = 0

    for bucket_def in DEFAULT_BUCKETS:
        if bucket_def["name"] in ("uncategorized", "knowledge"):
            continue
        rules = bucket_def["detection_rules"]
        keywords = rules.get("keywords", [])
        if not keywords:
            continue

        score = sum(1 for kw in keywords if kw.lower() in text_to_search)
        if score > best_score:
            best_score = score
            best_match = bucket_def["name"]

    if best_match and best_score >= 1:
        return bucket_map.get(best_match)

    # 3. Default to knowledge for single-turn Q&A, uncategorized for others
    if example.message_count <= 3:
        return bucket_map.get("knowledge")

    return bucket_map.get("uncategorized")


async def auto_bucket_dataset(db: AsyncSession, dataset_id: str):
    """Auto-assign buckets to all examples in a dataset."""
    bucket_map = await ensure_default_buckets(db)

    result = await db.execute(
        select(Example).where(Example.dataset_id == dataset_id)
    )
    examples = result.scalars().all()

    for example in examples:
        bucket_id = classify_example(example, bucket_map)
        if bucket_id:
            example.bucket_id = bucket_id

    await db.commit()
