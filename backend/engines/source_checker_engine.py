import logging
import math
import re

from backend.schemas.score import ScoreResult
from backend.utils.text_extraction import get_scoreable_text

logger = logging.getLogger(__name__)

# Regex patterns for content analysis
URL_PATTERN = re.compile(r'https?://[^\s<>"\')\]},;]+', re.IGNORECASE)
NUMBER_PATTERN = re.compile(r'\$[\d,.]+|\d{1,3}(?:,\d{3})*(?:\.\d+)?%?')
DATE_PATTERN = re.compile(
    r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s*\d{4}'
    r'|\d{1,2}/\d{1,2}/\d{2,4}'
    r'|\d{4}-\d{2}-\d{2}',
    re.IGNORECASE,
)
ENTITY_PATTERN = re.compile(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+')

# Red-flag patterns indicating low-quality / placeholder content
RED_FLAGS = [
    re.compile(r'\[.*?(insert|fill|placeholder|todo|tbd|your name|company name).*?\]', re.IGNORECASE),
    re.compile(r'lorem ipsum', re.IGNORECASE),
    re.compile(r'xxx+', re.IGNORECASE),
    re.compile(r'\{\{.*?\}\}'),  # template markers
    re.compile(r'<\w+>.*?</\w+>'),  # leftover HTML/XML tags
]

STOP_WORDS = {
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'can', 'shall', 'to', 'of', 'in', 'for',
    'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through', 'during',
    'and', 'but', 'or', 'nor', 'not', 'so', 'yet', 'both', 'either',
    'neither', 'this', 'that', 'these', 'those', 'it', 'its', 'i', 'me',
    'my', 'we', 'our', 'you', 'your', 'he', 'she', 'they', 'them',
}


class SourceCheckerEngine:
    """Analyzes training data content quality using regression analysis.

    Scores each example on:
    - Content length & completeness
    - Information density (entities, numbers, dates, specifics)
    - Vocabulary richness (type-token ratio)
    - Structural quality (sentence count, avg length, formatting)
    - Red flag detection (placeholders, templates, lorem ipsum)
    - Source reference quality (URLs present, proper citations)
    """

    name = "source_checker"

    def __init__(self):
        pass

    async def initialize(self) -> None:
        logger.info("SourceChecker engine initialized (content analysis mode)")

    async def score_batch(self, examples: list[dict]) -> list[ScoreResult]:
        """Score all examples by analyzing content quality."""
        results = []
        for ex in examples:
            scores = self._analyze_content(ex)
            results.extend(scores)
        return results

    def _analyze_content(self, example: dict) -> list[ScoreResult]:
        """Run regression analysis on a single example's content quality."""
        user_text = example.get("user_content", "") or ""
        assistant_text = example.get("assistant_content", "") or ""
        system_text = example.get("system_prompt", "") or ""
        full_text = get_scoreable_text(user_text, assistant_text)

        # --- Individual quality signals ---
        length_score = self._score_length(assistant_text)
        density_score = self._score_information_density(full_text)
        vocab_score = self._score_vocabulary_richness(assistant_text)
        structure_score = self._score_structure(assistant_text)
        red_flag_score = self._score_red_flags(full_text)
        completeness_score = self._score_completeness(user_text, assistant_text)
        source_ref_score = self._score_source_references(full_text)

        # --- Weighted regression: combine into overall source quality ---
        weights = {
            "length": 0.10,
            "density": 0.25,
            "vocabulary": 0.15,
            "structure": 0.15,
            "red_flags": 0.10,
            "completeness": 0.15,
            "source_refs": 0.10,
        }
        raw_scores = {
            "length": length_score,
            "density": density_score,
            "vocabulary": vocab_score,
            "structure": structure_score,
            "red_flags": red_flag_score,
            "completeness": completeness_score,
            "source_refs": source_ref_score,
        }

        weighted_sum = sum(raw_scores[k] * weights[k] for k in weights)
        total_weight = sum(weights.values())
        quality_score = weighted_sum / total_weight

        # Clamp to [0, 1]
        quality_score = max(0.0, min(1.0, quality_score))

        results = []

        # Primary score: source_quality (feeds into aggregate at 20% weight)
        results.append(ScoreResult(
            example_id=example["id"],
            engine_name=self.name,
            score_type="source_quality",
            score_value=round(quality_score, 4),
            raw_value=raw_scores,
            details=f"Content quality: {quality_score:.2f} (len={length_score:.2f}, density={density_score:.2f}, vocab={vocab_score:.2f})",
        ))

        # Secondary score: source_reachable (based on whether content has verifiable references)
        urls = URL_PATTERN.findall(full_text)
        has_refs = len(urls) > 0 or len(DATE_PATTERN.findall(full_text)) > 0 or len(ENTITY_PATTERN.findall(full_text)) > 2
        results.append(ScoreResult(
            example_id=example["id"],
            engine_name=self.name,
            score_type="source_reachable",
            score_value=1.0 if has_refs else 0.5,
            raw_value={"has_references": has_refs, "url_count": len(urls)},
            details=f"{'Has' if has_refs else 'No'} verifiable references",
        ))

        return results

    def _score_length(self, text: str) -> float:
        """Score based on response length. Sweet spot: 100-2000 chars."""
        length = len(text)
        if length < 20:
            return 0.2
        elif length < 50:
            return 0.4
        elif length < 100:
            return 0.6
        elif length <= 2000:
            # Peak quality range
            return 0.8 + 0.2 * min(1.0, length / 500)
        elif length <= 5000:
            return 0.9
        else:
            # Very long responses slightly penalized
            return 0.85

    def _score_information_density(self, text: str) -> float:
        """Score based on specific facts: numbers, dates, proper nouns, entities."""
        if not text:
            return 0.3

        words = text.split()
        word_count = len(words)
        if word_count < 5:
            return 0.3

        numbers = NUMBER_PATTERN.findall(text)
        dates = DATE_PATTERN.findall(text)
        entities = ENTITY_PATTERN.findall(text)
        urls = URL_PATTERN.findall(text)

        # Count specific facts per 100 words
        fact_count = len(numbers) + len(dates) + len(entities) + len(urls)
        density = (fact_count / word_count) * 100

        if density >= 8:
            return 0.95
        elif density >= 5:
            return 0.85
        elif density >= 3:
            return 0.75
        elif density >= 1:
            return 0.65
        else:
            return 0.5

    def _score_vocabulary_richness(self, text: str) -> float:
        """Type-token ratio: unique words / total words."""
        if not text:
            return 0.3

        words = [w.lower() for w in re.findall(r'\b\w+\b', text)]
        content_words = [w for w in words if w not in STOP_WORDS and len(w) > 2]

        if len(content_words) < 5:
            return 0.5

        unique = len(set(content_words))
        total = len(content_words)
        ttr = unique / total

        # Adjust for text length (longer texts naturally have lower TTR)
        adjusted_ttr = ttr * math.log(total + 1) / math.log(50)
        adjusted_ttr = min(1.0, adjusted_ttr)

        if adjusted_ttr >= 0.8:
            return 0.95
        elif adjusted_ttr >= 0.6:
            return 0.85
        elif adjusted_ttr >= 0.4:
            return 0.75
        elif adjusted_ttr >= 0.25:
            return 0.65
        else:
            return 0.5

    def _score_structure(self, text: str) -> float:
        """Score structural quality: sentence variety, paragraphs, formatting."""
        if not text:
            return 0.3

        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        sent_count = len(sentences)

        if sent_count == 0:
            return 0.3

        # Average sentence length
        avg_sent_len = sum(len(s.split()) for s in sentences) / sent_count

        # Sentence length variety (std dev)
        sent_lengths = [len(s.split()) for s in sentences]
        if len(sent_lengths) > 1:
            mean_len = sum(sent_lengths) / len(sent_lengths)
            variance = sum((x - mean_len) ** 2 for x in sent_lengths) / len(sent_lengths)
            std_dev = math.sqrt(variance)
        else:
            std_dev = 0

        score = 0.5

        # Good average sentence length (10-25 words)
        if 10 <= avg_sent_len <= 25:
            score += 0.15
        elif 5 <= avg_sent_len <= 35:
            score += 0.08

        # Multiple sentences
        if sent_count >= 3:
            score += 0.15
        elif sent_count >= 2:
            score += 0.08

        # Sentence variety
        if std_dev > 3:
            score += 0.1

        # Has paragraphs or formatting
        if '\n' in text:
            score += 0.05

        # Has lists or bullet points
        if re.search(r'(?:^|\n)\s*[-•*\d]+[.)]\s', text):
            score += 0.05

        return min(1.0, score)

    def _score_red_flags(self, text: str) -> float:
        """Score inversely to red flags found. 1.0 = no red flags."""
        if not text:
            return 0.5

        flag_count = 0
        for pattern in RED_FLAGS:
            matches = pattern.findall(text)
            flag_count += len(matches)

        if flag_count == 0:
            return 1.0
        elif flag_count == 1:
            return 0.6
        elif flag_count <= 3:
            return 0.3
        else:
            return 0.1

    def _score_completeness(self, user_text: str, assistant_text: str) -> float:
        """Score how completely the assistant answers the user query."""
        if not user_text or not assistant_text:
            return 0.5

        # Check if assistant response is substantially longer than the question
        ratio = len(assistant_text) / max(len(user_text), 1)

        # Extract question words from user
        user_words = set(w.lower() for w in re.findall(r'\b\w+\b', user_text)) - STOP_WORDS
        assistant_words = set(w.lower() for w in re.findall(r'\b\w+\b', assistant_text)) - STOP_WORDS

        # Topic coverage: how many user topic words appear in the response
        if user_words:
            coverage = len(user_words & assistant_words) / len(user_words)
        else:
            coverage = 0.5

        score = 0.4

        # Length ratio bonus
        if ratio >= 3:
            score += 0.25
        elif ratio >= 1.5:
            score += 0.15
        elif ratio >= 0.5:
            score += 0.05

        # Topic coverage bonus
        score += coverage * 0.35

        return min(1.0, score)

    def _score_source_references(self, text: str) -> float:
        """Score presence of verifiable source references."""
        if not text:
            return 0.5

        urls = URL_PATTERN.findall(text)
        entities = ENTITY_PATTERN.findall(text)
        numbers = NUMBER_PATTERN.findall(text)
        dates = DATE_PATTERN.findall(text)

        score = 0.5

        # URLs indicate sourced content
        if urls:
            score += min(0.2, len(urls) * 0.07)

        # Named entities suggest specific, factual content
        if len(entities) >= 3:
            score += 0.15
        elif entities:
            score += 0.08

        # Numbers/stats suggest data-backed content
        if len(numbers) >= 2:
            score += 0.1
        elif numbers:
            score += 0.05

        # Dates suggest timely, specific content
        if dates:
            score += 0.05

        return min(1.0, score)

    async def health_check(self) -> bool:
        return True

    async def shutdown(self) -> None:
        pass
