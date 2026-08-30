"""
Deduplicator — utilities to remove duplicate retrieved chunks, redundant sentences, and repeated facts.
"""
import re
from typing import Sequence
from langchain_core.documents import Document


def normalize_text(text: str) -> str:
    """Normalize text for similarity and equality comparison."""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text


def deduplicate_documents(documents: Sequence[Document], similarity_threshold: float = 0.85) -> list[Document]:
    """
    Remove exact duplicate and highly overlapping documents/chunks from retrieval.
    Preserves the original order (ranking).
    """
    unique_docs: list[Document] = []
    seen_normalized: list[str] = []

    for doc in documents:
        content = doc.page_content.strip()
        if not content:
            continue

        norm = normalize_text(content)
        if not norm:
            continue

        # Exact match check
        if norm in seen_normalized:
            continue

        # Overlap / containment check
        is_duplicate = False
        norm_words = set(norm.split())
        for prev_norm in seen_normalized:
            prev_words = set(prev_norm.split())
            if not norm_words or not prev_words:
                continue

            intersection = len(norm_words & prev_words)
            smaller_len = min(len(norm_words), len(prev_words))

            if smaller_len > 0 and (intersection / smaller_len) >= similarity_threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            unique_docs.append(doc)
            seen_normalized.append(norm)

    return unique_docs


def deduplicate_sentences(text: str) -> str:
    """
    Remove repeated sentences or phrases from an answer to ensure concise, non-repeating output.
    """
    if not text:
        return text

    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append("")
            continue

        # Split into sentences or comma-separated items
        parts = re.split(r"(?<=[.!?])\s+", stripped)
        seen_parts = set()
        kept_parts = []

        for p in parts:
            p_norm = normalize_text(p)
            if p_norm and p_norm not in seen_parts:
                seen_parts.add(p_norm)
                kept_parts.append(p)

        if kept_parts:
            cleaned_lines.append(" ".join(kept_parts))

    # Remove repeated adjacent lines
    deduped_lines = []
    prev_norm = ""
    for line in cleaned_lines:
        line_norm = normalize_text(line)
        if line_norm and line_norm == prev_norm:
            continue
        deduped_lines.append(line)
        if line_norm:
            prev_norm = line_norm

    return "\n".join(deduped_lines).strip()
