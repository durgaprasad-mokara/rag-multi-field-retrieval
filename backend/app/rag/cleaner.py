"""
Text Cleaner & Normalizer — cleans extracted document text before chunking and embedding.
Preserves meaning, names, dates, numbers, technical terms, tables, and document structure
while removing formatting noise, excessive whitespace, and duplicate content.
"""
import re
from typing import List


def clean_extracted_text(text: str) -> str:
    """
    Clean extracted document text before chunking without altering meaning.

    Preserves:
    - Names, phone numbers, email addresses, URLs
    - Dates, numbers, currency, percentages
    - Programming languages, technical terms (e.g. 'Machine Learning')
    - Bullet points, headings, table structures
    - Standard punctuation and sentence casing
    """
    if not text:
        return ""

    # 1. Remove non-printable / control characters (keep \t, \n, \r)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)

    # 2. Normalize Windows / Mac line endings to standard \n
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 3. Clean line by line to preserve structure (lists, tables, headings)
    lines = text.split("\n")
    cleaned_lines: List[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append("")
            continue

        # If line is a markdown / ASCII table row (e.g. | col1 | col2 |), preserve row structure
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [re.sub(r"[ \t]+", " ", c.strip()) for c in stripped.split("|")]
            cleaned_lines.append("| " + " | ".join(cells[1:-1]) + " |")
            continue

        # Normalize multiple spaces / tabs within a normal line to a single space
        norm_line = re.sub(r"[ \t]+", " ", stripped)

        # Fix noisy OCR repeated commas or periods (e.g. ',,,,,' -> ',', '.....' -> '...')
        norm_line = re.sub(r",{2,}", ",", norm_line)
        norm_line = re.sub(r"(?<!\.)\.\.(?!\.)", ".", norm_line)

        # Normalize repeated words caused by extraction glitch (e.g. "John Smith John Smith" at line start)
        words = norm_line.split()
        if len(words) >= 4 and len(words) % 2 == 0:
            half = len(words) // 2
            if [w.lower() for w in words[:half]] == [w.lower() for w in words[half:]]:
                norm_line = " ".join(words[:half])

        # Normalize repeated single words (e.g. "the the the" -> "the", "and and" -> "and")
        norm_line = re.sub(r"\b(\w+)(?:\s+\1\b){2,}", r"\1", norm_line, flags=re.IGNORECASE)

        cleaned_lines.append(norm_line)

    # 4. Normalize multiple consecutive empty lines to a maximum of 2 (paragraph break)
    result = "\n".join(cleaned_lines)
    result = re.sub(r"\n{3,}", "\n\n", result)

    # 5. Remove accidental exact duplicate paragraphs
    result = deduplicate_paragraphs(result)

    return result.strip()


def deduplicate_paragraphs(text: str) -> str:
    """
    Remove exact duplicate adjacent or section-level paragraphs before embedding.
    """
    if not text:
        return text

    paragraphs = text.split("\n\n")
    unique_paragraphs: List[str] = []
    seen_norm: set[str] = set()

    for p in paragraphs:
        p_clean = p.strip()
        if not p_clean:
            continue

        # Normalize for deduplication comparison
        p_norm = re.sub(r"\s+", " ", p_clean.lower())
        
        # If very short line (e.g. a heading or single bullet), allow contextual repetition
        if len(p_clean.split()) <= 3:
            unique_paragraphs.append(p_clean)
            continue

        if p_norm not in seen_norm:
            seen_norm.add(p_norm)
            unique_paragraphs.append(p_clean)

    return "\n\n".join(unique_paragraphs)
