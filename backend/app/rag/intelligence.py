"""
AI/ML Intelligence Layer — lightweight query classification, intent detection,
query routing, retrieval relevance scoring, confidence estimation, and query expansion.

Design principles:
- Reuses existing BAAI/bge-small-en-v1.5 embeddings (no new models)
- Uses deterministic logic + optional cosine similarity (numpy)
- Every function has safe error handling — failures return defaults, never crash
- Pure functions — no side effects, no database access
- No custom model training required
"""
import os
import re
import logging
import time
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# 1. QUERY CLASSIFICATION
# ══════════════════════════════════════════════════════════════

# Classification patterns — ordered by specificity (most specific first)
_MULTI_FIELD_PATTERNS = [
    r"\b(?:and|,)\b.*\b(?:and|,)\b",   # Multiple conjunctions/commas
    r"\bgive\s+(?:me\s+)?(?:all|my)\b.*\b(?:and|,)\b",
    r"\bwhat\s+(?:are|is)\s+my\b.*\b(?:and|,)\b",
    r"\blist\s+(?:all|my)\b.*\b(?:and|,)\b",
]

_SUMMARY_PATTERNS = [
    r"\bsummar(?:y|ize|ise)\b",
    r"\boverview\b",
    r"\bbrief(?:ly)?\b",
    r"\bhighlight(?:s)?\b",
    r"\bwhat\s+(?:does|is)\s+(?:this|the)\s+document\s+(?:about|cover|contain)\b",
    r"\btell\s+me\s+about\s+(?:this|the)\s+document\b",
]

_COMPARISON_PATTERNS = [
    r"\bcompar(?:e|ison)\b",
    r"\bdifference(?:s)?\s+between\b",
    r"\bvs\.?\b",
    r"\bbetter\s+than\b",
    r"\bsimilar(?:ity|ities)?\s+(?:between|to)\b",
]

_ANALYTICAL_PATTERNS = [
    r"\bwhy\b.*\b(?:is|are|did|does|was|were)\b",
    r"\bhow\s+(?:does|did|can|could|would|should)\b",
    r"\bexplain\b",
    r"\banalyze\b",
    r"\btrend(?:s)?\b",
    r"\bimpact\b",
    r"\brelationship\s+between\b",
]

_CONVERSATIONAL_PATTERNS = [
    r"^(?:tell\s+me\s+more|go\s+on|continue|elaborate|what\s+else)\b",
    r"^(?:and\s+)?(?:what\s+about|how\s+about)\b",
    r"^(?:also|additionally)\b",
]

_UNSUPPORTED_PATTERNS = [
    r"\bweather\b",
    r"\bstock\s+(?:price|market)\b",
    r"\bcurrent\s+(?:time|date)\b",
    r"\bwho\s+is\s+the\s+president\b",
    r"\blatest\s+news\b",
    r"\bplay\s+(?:music|song|video)\b",
    r"\bset\s+(?:a\s+)?(?:timer|alarm|reminder)\b",
]


def classify_query(question: str) -> str:
    """
    Classify a user question into a query type.

    Returns one of:
        factual_lookup | multi_field | summary | comparison |
        analytical | conversational | unsupported

    Falls back to 'factual_lookup' on any error.
    """
    try:
        q_lower = question.lower().strip()

        # Check unsupported first (quick exit)
        for pattern in _UNSUPPORTED_PATTERNS:
            if re.search(pattern, q_lower):
                return "unsupported"

        # Check conversational
        for pattern in _CONVERSATIONAL_PATTERNS:
            if re.search(pattern, q_lower):
                return "conversational"

        # Check summary
        for pattern in _SUMMARY_PATTERNS:
            if re.search(pattern, q_lower):
                return "summary"

        # Check comparison
        for pattern in _COMPARISON_PATTERNS:
            if re.search(pattern, q_lower):
                return "comparison"

        # Check analytical
        for pattern in _ANALYTICAL_PATTERNS:
            if re.search(pattern, q_lower):
                return "analytical"

        # Check multi-field (requires importing field detection)
        # First check structural patterns
        for pattern in _MULTI_FIELD_PATTERNS:
            if re.search(pattern, q_lower):
                return "multi_field"

        # Also check using the existing field catalog
        try:
            from app.rag.multi_field import decompose_query
            fields = decompose_query(question)
            if len(fields) >= 2:
                return "multi_field"
        except Exception:
            pass

        # Default: factual lookup
        return "factual_lookup"

    except Exception as e:
        logger.warning(f"classify_query failed, defaulting to factual_lookup: {e}")
        return "factual_lookup"


# ══════════════════════════════════════════════════════════════
# 2. INTENT DETECTION
# ══════════════════════════════════════════════════════════════

# Intent mapping — maps intent names to keyword patterns
_INTENT_PATTERNS: Dict[str, List[str]] = {
    "skills": ["skill", "skills", "competenc", "abilit", "proficienc", "tech stack", "technologies", "programming", "frameworks", "tools"],
    "education": ["education", "degree", "university", "college", "academic", "school", "gpa", "cgpa", "qualification", "bachelor", "master"],
    "contact": ["phone", "mobile", "email", "mail", "contact", "telephone", "cell"],
    "linkedin": ["linkedin"],
    "github": ["github", "git hub"],
    "portfolio": ["portfolio", "website", "blog"],
    "projects": ["project", "projects", "built", "developed", "implemented"],
    "experience": ["experience", "employment", "work history", "internship", "company", "role", "job"],
    "certifications": ["certification", "certificate", "license", "course"],
    "name": ["name", "who is", "candidate name", "employee name"],
    "summary": ["summary", "about", "objective", "overview", "profile"],
    "benefits": ["benefit", "perks", "allowance", "compensation"],
    "policy": ["policy", "leave", "rules", "guidelines", "regulations"],
    "languages": ["languages", "spoken", "fluent"],
    "video_content": ["video", "speaker", "timestamp", "minute", "discussed"],
}


def detect_intent(question: str, query_type: str = "factual_lookup") -> str:
    """
    Detect the user's primary intent from the question.

    Returns the best matching intent key (e.g., 'skills', 'education', 'contact').
    Falls back to 'general' if no specific intent is detected.
    """
    try:
        q_lower = question.lower().strip()

        # Score each intent by keyword matches
        best_intent = "general"
        best_score = 0

        for intent, keywords in _INTENT_PATTERNS.items():
            score = 0
            for kw in keywords:
                if kw in q_lower:
                    # Longer keyword matches get higher weight
                    score += len(kw.split())
            if score > best_score:
                best_score = score
                best_intent = intent

        # For multi_field queries, also try to identify the primary intent
        if query_type == "multi_field" and best_intent == "general":
            # Use the first detected field as primary intent
            try:
                from app.rag.multi_field import decompose_query
                fields = decompose_query(question)
                if fields:
                    best_intent = fields[0].key
            except Exception:
                pass

        return best_intent

    except Exception as e:
        logger.warning(f"detect_intent failed, defaulting to general: {e}")
        return "general"


# ══════════════════════════════════════════════════════════════
# 3. QUERY ROUTING
# ══════════════════════════════════════════════════════════════

def route_query(query_type: str, intent: str, field_count: int = 0,
                target_response_time: float = 2.0) -> Dict[str, Any]:
    """
    Determine the retrieval strategy based on classification, intent, and constraints.

    Returns:
        {
            "strategy": str,    # targeted | field_level | broad | expanded | fallback
            "k": int,           # number of chunks to retrieve
            "max_chars": int,   # context budget in characters
        }
    """
    try:
        # Adapt retrieval budget to target response time
        if target_response_time <= 1.0:
            base_k, base_chars = 3, 2500
        elif target_response_time <= 5.0:
            base_k, base_chars = 5, 4500
        else:
            base_k, base_chars = 8, 8000

        if query_type == "unsupported":
            return {"strategy": "fallback", "k": 0, "max_chars": 0}

        if query_type == "multi_field":
            # Multi-field: retrieve more chunks per field
            k = max(15, base_k * 3)
            return {"strategy": "field_level", "k": k, "max_chars": base_chars + 2000}

        if query_type == "summary":
            k = max(10, base_k * 2)
            return {"strategy": "broad", "k": k, "max_chars": base_chars + 1000}

        if query_type == "comparison":
            k = max(10, base_k * 2)
            return {"strategy": "broad", "k": k, "max_chars": base_chars + 1000}

        if query_type == "analytical":
            k = max(8, base_k + 3)
            return {"strategy": "expanded", "k": k, "max_chars": base_chars + 1500}

        if query_type == "conversational":
            return {"strategy": "targeted", "k": base_k, "max_chars": base_chars}

        # Default: factual_lookup
        return {"strategy": "targeted", "k": max(5, base_k), "max_chars": base_chars}

    except Exception as e:
        logger.warning(f"route_query failed, defaulting to targeted: {e}")
        return {"strategy": "targeted", "k": 5, "max_chars": 4500}


# ══════════════════════════════════════════════════════════════
# 4. RETRIEVAL RELEVANCE SCORING
# ══════════════════════════════════════════════════════════════

def _cosine_similarity(vec_a, vec_b) -> float:
    """Compute cosine similarity between two vectors using numpy."""
    try:
        import numpy as np
        a = np.array(vec_a, dtype=np.float32)
        b = np.array(vec_b, dtype=np.float32)
        dot = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(dot / (norm_a * norm_b))
    except Exception:
        return 0.0


def score_retrieval_relevance(
    question: str,
    chunks: list,
    embeddings_model=None,
) -> Tuple[list, str]:
    """
    Score retrieved chunks for relevance using embedding cosine similarity.

    IMPORTANT: This function ANNOTATES chunks with scores but does NOT remove
    any chunks. Distinct field evidence is always preserved.

    Args:
        question: The user's query
        chunks: List of LangChain Document objects
        embeddings_model: Optional embeddings instance for cosine similarity

    Returns:
        (scored_chunks, confidence_level)
        - scored_chunks: Same chunks with 'relevance_score' added to metadata
        - confidence_level: "high" | "medium" | "low" | "insufficient"
    """
    try:
        if not chunks:
            return chunks, "insufficient"

        scored_chunks = list(chunks)

        # Try embedding-based scoring if embeddings are available
        if embeddings_model is not None:
            try:
                query_embedding = embeddings_model.embed_query(question)
                chunk_texts = [c.page_content[:500] for c in scored_chunks]
                chunk_embeddings = embeddings_model.embed_documents(chunk_texts)

                scores = []
                for i, chunk in enumerate(scored_chunks):
                    sim = _cosine_similarity(query_embedding, chunk_embeddings[i])
                    chunk.metadata["relevance_score"] = round(sim, 4)
                    scores.append(sim)

                # Determine confidence from score distribution
                if scores:
                    avg_score = sum(scores) / len(scores)
                    max_score = max(scores)

                    if max_score >= 0.7 and avg_score >= 0.5:
                        confidence = "high"
                    elif max_score >= 0.5 and avg_score >= 0.35:
                        confidence = "medium"
                    elif max_score >= 0.3:
                        confidence = "low"
                    else:
                        confidence = "insufficient"

                    return scored_chunks, confidence

            except Exception as e:
                logger.debug(f"Embedding-based scoring failed, using fallback: {e}")

        # Fallback: keyword-based scoring
        q_words = set(re.sub(r"[^\w\s]", "", question.lower()).split())
        stop_words = {"what", "is", "the", "a", "an", "are", "my", "me", "give", "tell",
                      "show", "all", "of", "in", "for", "and", "or", "to", "how", "does"}
        q_keywords = q_words - stop_words

        if not q_keywords:
            # No meaningful keywords — mark all as medium
            for chunk in scored_chunks:
                chunk.metadata["relevance_score"] = 0.5
            return scored_chunks, "medium"

        scores = []
        for chunk in scored_chunks:
            chunk_words = set(re.sub(r"[^\w\s]", "", chunk.page_content.lower()).split())
            overlap = len(q_keywords & chunk_words)
            score = overlap / len(q_keywords) if q_keywords else 0.0
            chunk.metadata["relevance_score"] = round(min(score, 1.0), 4)
            scores.append(score)

        avg_score = sum(scores) / len(scores) if scores else 0.0
        max_score = max(scores) if scores else 0.0

        if max_score >= 0.6 and avg_score >= 0.4:
            confidence = "high"
        elif max_score >= 0.4 and avg_score >= 0.25:
            confidence = "medium"
        elif max_score >= 0.2:
            confidence = "low"
        else:
            confidence = "insufficient"

        return scored_chunks, confidence

    except Exception as e:
        logger.warning(f"score_retrieval_relevance failed: {e}")
        return chunks, "medium"


# ══════════════════════════════════════════════════════════════
# 5. ANSWER CONFIDENCE ESTIMATION
# ══════════════════════════════════════════════════════════════

def estimate_answer_confidence(
    requested_fields: list,
    answered_fields: list,
    retrieval_confidence: str = "medium",
    validation_passed: bool = True,
) -> str:
    """
    Estimate overall answer confidence.

    Used for diagnostics and tracing only — NOT displayed to users as a probability.

    Returns: "high" | "medium" | "low" | "insufficient"
    """
    try:
        # No fields requested — single question
        if not requested_fields:
            if retrieval_confidence == "high" and validation_passed:
                return "high"
            elif retrieval_confidence in ("high", "medium") and validation_passed:
                return "medium"
            elif validation_passed:
                return "low"
            else:
                return "insufficient"

        # Multi-field: check coverage
        total = len(requested_fields)
        answered = len(answered_fields) if answered_fields else 0

        if total == 0:
            return "medium"

        coverage = answered / total

        if coverage >= 0.9 and retrieval_confidence in ("high", "medium") and validation_passed:
            return "high"
        elif coverage >= 0.6 and validation_passed:
            return "medium"
        elif coverage >= 0.3:
            return "low"
        else:
            return "insufficient"

    except Exception as e:
        logger.warning(f"estimate_answer_confidence failed: {e}")
        return "medium"


# ══════════════════════════════════════════════════════════════
# 6. QUERY EXPANSION
# ══════════════════════════════════════════════════════════════

def expand_query(question: str, intent: str, detected_fields: list = None) -> List[str]:
    """
    Generate expanded search terms when retrieval confidence is low.

    Uses intent + field catalog synonyms + retrieval keywords to broaden search.
    Only invoked when retrieval_confidence == "low" or "insufficient".

    Returns: List of additional search term strings.
    """
    try:
        if not os.getenv("AI_ML_QUERY_EXPANSION_ENABLED", "true").lower() == "true":
            return []

        expansion_terms = []

        # Use intent keywords
        if intent in _INTENT_PATTERNS:
            for kw in _INTENT_PATTERNS[intent]:
                if kw.lower() not in question.lower():
                    expansion_terms.append(kw)

        # Use detected field retrieval keywords
        if detected_fields:
            for field in detected_fields:
                for kw in getattr(field, "retrieval_keywords", []):
                    if kw.lower() not in question.lower() and kw not in expansion_terms:
                        expansion_terms.append(kw)

        # Limit expansion to avoid excessive retrieval
        return expansion_terms[:8]

    except Exception as e:
        logger.warning(f"expand_query failed: {e}")
        return []


# ══════════════════════════════════════════════════════════════
# 7. QUERY COMPLEXITY DETECTION
# ══════════════════════════════════════════════════════════════

def estimate_query_complexity(question: str, query_type: str, field_count: int = 0) -> str:
    """
    Estimate query complexity for performance routing.

    Returns: "simple" | "moderate" | "complex"
    """
    try:
        if query_type == "unsupported":
            return "simple"

        word_count = len(question.split())

        if query_type in ("analytical", "comparison") or word_count > 30:
            return "complex"

        if query_type == "multi_field" and field_count >= 4:
            return "complex"

        if query_type in ("summary", "multi_field") or word_count > 15:
            return "moderate"

        return "simple"

    except Exception:
        return "moderate"
