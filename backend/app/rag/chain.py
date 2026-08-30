"""
RAG chain — composes retriever + prompt + LLM into a complete chain.
Supports Local Grounded Extractor (offline CPU), OpenAI, OpenRouter, and Ollama.
"""
import os
import re
from typing import Any, Optional, List, Dict
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.retrievers import BaseRetriever
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration

from app.rag.prompts import get_rag_prompt
from app.rag.deduplicator import deduplicate_sentences, normalize_text

FALLBACK_MSG = "Information not found in the selected document."

# Common section header keywords across diverse document types
SECTION_KEYWORDS = [
    "skill", "skills", "technical skills", "core competencies", "competencies",
    "benefit", "benefits", "employee benefits", "perks", "compensation",
    "objective", "objectives", "research objectives", "course objectives", "goals",
    "project", "projects", "key projects", "past projects",
    "education", "academic background", "qualifications", "degree",
    "experience", "work experience", "employment", "professional experience",
    "summary", "profile summary", "executive summary", "overview", "about",
    "policy", "policies", "leave policy", "vacation policy", "rules", "guidelines",
    "conclusion", "conclusions", "findings", "key findings", "results",
    "certification", "certifications", "licenses", "courses", "subjects",
    "publication", "publications", "references", "responsibilities", "duties",
    "requirement", "requirements", "prerequisites", "eligibility",
    "protocol", "methodology", "methods", "abstract", "introduction",
]


def _is_heading(line: str) -> bool:
    """Determine if a single line is a section heading."""
    clean = line.strip()
    if not clean:
        return False
    if clean.startswith("#"):
        return True
    
    # Strip trailing colon or dashes
    stripped = clean.rstrip(":-=").strip()
    if not stripped:
        return False

    # Standalone exact keyword phrase
    low = stripped.lower()
    if low in SECTION_KEYWORDS:
        return True

    # Uppercase lines with 1-6 words (e.g. "TECHNICAL SKILLS", "EMPLOYEE BENEFITS", "SUMMARY")
    words = stripped.split()
    if 1 <= len(words) <= 6 and stripped.isupper() and any(c.isalpha() for c in stripped):
        return True

    # Short line ending with colon (e.g. "Skills:", "Benefits:", "Course Objectives:")
    if clean.endswith(":") and len(words) <= 6:
        return True

    return False


def _parse_sections(lines: list[str]) -> list[Dict[str, Any]]:
    """Parse flat lines of document text into structured sections with headers and bodies."""
    sections: list[Dict[str, Any]] = []
    current_header = ""
    current_body: list[str] = []

    for line in lines:
        clean = line.strip()
        if not clean:
            continue

        if _is_heading(clean):
            if current_header or current_body:
                sections.append({
                    "header": current_header,
                    "body": current_body,
                    "raw_header": current_header
                })
            current_header = clean.lstrip("#").rstrip(":-=").strip()
            current_body = []
        else:
            current_body.append(clean)

    if current_header or current_body:
        sections.append({
            "header": current_header,
            "body": current_body,
            "raw_header": current_header
        })

    return sections


def _is_list_line(line: str) -> bool:
    """Check if a line looks like a list item rather than a full narrative sentence."""
    clean = line.strip()
    if re.match(r"^(?:[-*•·–—]\s+|\d+[\.)]\s+)", clean):
        return True
    if ":" in clean and not clean.startswith(("http:", "https:")):
        return True
    return False


def _extract_items_from_body(body_lines: list[str], section_header: str = "") -> list[str]:
    """Extract individual items, list points, or comma-separated elements from section lines."""
    items: list[str] = []
    seen = set()

    is_explicit_list_section = any(kw in section_header.lower() for kw in [
        "skill", "skills", "competencies", "benefit", "benefits", "perks",
        "technologies", "tools", "languages", "frameworks", "databases", "platforms"
    ])

    for line in body_lines:
        clean = line.strip()
        if not clean:
            continue

        # If line contains category prefix e.g. "Programming: Python, Java, C++"
        if ":" in clean and not clean.startswith(("http:", "https:")):
            parts = clean.split(":", 1)
            val_part = parts[1].strip()
            if val_part:
                sub_items = [s.strip() for s in re.split(r"[,;|•·/]", val_part) if s.strip()]
                for it in sub_items:
                    norm = it.lower()
                    if norm not in seen and len(it) > 0:
                        seen.add(norm)
                        items.append(it)
                continue

        # If line is explicitly bulleted / numbered
        if re.match(r"^(?:[-*•·–—]\s+|\d+[\.)]\s+)", clean):
            clean_bullet = re.sub(r"^(?:[-*•·–—]\s+|\d+[\.)]\s+)", "", clean).strip()
            norm = clean_bullet.lower()
            if norm not in seen and len(clean_bullet) > 0:
                seen.add(norm)
                items.append(clean_bullet)
            continue

        # If section is an explicit list/skill/benefit section where each line is an item
        if is_explicit_list_section:
            if "," in clean:
                sub_items = [s.strip() for s in clean.split(",") if s.strip()]
                if all(len(s.split()) <= 4 for s in sub_items):
                    for it in sub_items:
                        norm = it.lower()
                        if norm not in seen and len(it) > 0:
                            seen.add(norm)
                            items.append(it)
                    continue
            norm = clean.lower()
            if norm not in seen and len(clean) > 0:
                seen.add(norm)
                items.append(clean)
            continue

        # Otherwise preserve line as a whole
        norm = clean.lower()
        if norm not in seen and len(clean) > 0:
            seen.add(norm)
            items.append(clean)

    return items


def _parse_table_data(lines: list[str], question_lower: str) -> Optional[str]:
    """Parse pipe-delimited markdown / ASCII tables and extract requested values."""
    table_lines = [l for l in lines if "|" in l]
    if len(table_lines) < 2:
        return None

    rows = []
    for tl in table_lines:
        cells = [c.strip() for c in tl.strip().strip("|").split("|")]
        if cells and not all(re.match(r"^:?-+:?$", c) for c in cells):
            rows.append(cells)

    if len(rows) < 2:
        return None

    headers = [h.lower() for h in rows[0]]
    data_rows = rows[1:]

    # Check if user asks for a specific cell e.g. "What is Python skill level?"
    for row in data_rows:
        if not row:
            continue
        row_str = " ".join(row).lower()
        # Find matching row
        for i, cell in enumerate(row):
            cell_lower = cell.lower()
            if cell_lower and cell_lower in question_lower:
                # Target column in question
                for j, h in enumerate(headers):
                    if j != i and j < len(row) and h in question_lower:
                        return row[j]
                # Return the other column if 2 columns
                if len(row) == 2:
                    return row[1] if i == 0 else row[0]

    # Check if user asks for an entire column e.g. "What skills are listed?"
    for j, h in enumerate(headers):
        if h in question_lower or any(w in h for w in question_lower.split()):
            col_items = [r[j] for r in data_rows if j < len(r) and r[j]]
            if col_items:
                return "\n".join(f"- {it}" for it in col_items)

    return None


class LocalGroundedChatModel(BaseChatModel):
    """
    High-precision universal document extractor.
    Extracts exact requested content from sections, lists, tables, narrative text,
    and key-value pairs while strictly preventing section-heading-only answers.
    """

    def _extract_exact_answer(self, question: str, context: str) -> str:
        if not context or not context.strip():
            return FALLBACK_MSG

        q_clean = question.strip()
        q_lower = q_clean.lower()
        q_text = re.sub(r"[?!.,'\"`]", "", q_lower).strip()

        stopwords = {
            "what", "is", "the", "a", "an", "are", "were", "was", "of", "in", "for",
            "to", "and", "or", "tell", "me", "give", "show", "who", "whom", "whose",
            "where", "when", "why", "how", "does", "did", "can", "could", "all",
            "candidate", "candidates", "student", "students", "company", "companys",
            "document", "documents", "file", "files", "list", "set", "details",
            "information", "about", "provide", "please", "mentioned", "any"
        }
        q_words = [w for w in q_text.split() if w not in stopwords and len(w) > 1]

        lines = [line.strip() for line in context.splitlines() if line.strip()]

        # ── 1. Person / Entity Disambiguation ──────────────────────────
        # Check if question specifies a distinct person/entity name not in context
        person_names_in_q = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", question)
        for pn in person_names_in_q:
            pn_lower = pn.lower()
            if not any(w in pn_lower for w in ["what", "where", "who", "when", "how", "why", "information", "candidate", "student", "employee", "company", "document"]):
                if pn_lower not in context.lower():
                    return FALLBACK_MSG

        # ── 2. Candidate / Employee / Person Name Fast-Paths ──────────
        if "name" in q_text and not any(w in q_text for w in ["company", "organization", "college", "university", "tool", "file", "skill", "category", "type", "document"]):
            for line in lines:
                m = re.search(r"^(?:candidate\s+name|student\s+name|author\s+name|employee\s+name|employee\s+profile|student\s+profile|candidate\s+profile|employee|candidate|student|full\s+name|name)\s*[:=-]\s*(.+)$", line, re.I)
                if m:
                    return m.group(1).strip()
            # If document starts with a person name (1st line: 2-3 capitalized words)
            if lines and not lines[0].startswith("#") and ":" not in lines[0]:
                first_line = lines[0].strip()
                disallowed_words = [
                    "policy", "policies", "manual", "guide", "handbook", "protocol", "report",
                    "company", "inc", "corp", "ltd", "notes", "foundations", "document",
                    "documentation", "terms", "service", "agreement", "rules", "plan", "trial",
                    "university", "college", "school", "department", "curriculum", "resume", "cv",
                    "table", "overview", "introduction"
                ]
                if not any(dw in first_line.lower() for dw in disallowed_words):
                    first_words = first_line.split()
                    if 2 <= len(first_words) <= 3 and all(w[0].isupper() for w in first_words if w.isalpha()):
                        return first_line

        # ── 3. Contact Details / Specific Attributes ───────────────────
        # Phone
        if any(w in q_text for w in ["phone", "mobile", "contact number", "telephone", "cell"]):
            for line in lines:
                if any(k in line.lower() for k in ["phone", "mobile", "tel", "contact"]):
                    m = re.search(r"(?:phone|mobile|tel|contact(?:\s+number)?)\s*[:=-]\s*([^\s|;,]+(?:\s+[^\s|;,]+)*)", line, re.I)
                    if m:
                        val = m.group(1).strip()
                        # If val contains a phone-like number
                        if any(c.isdigit() for c in val):
                            return val
            phone_match = re.search(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,5}\)?[-.\s]?\d{3,5}[-.\s]?\d{3,5}", context)
            if phone_match and len(re.sub(r"\D", "", phone_match.group(0))) >= 7:
                return phone_match.group(0).strip()

        # Email
        if any(w in q_text for w in ["email", "e-mail", "mail"]):
            email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", context)
            if email_match:
                return email_match.group(0).strip()

        # CGPA / GPA / Grade / Score
        if any(w in q_text for w in ["cgpa", "gpa", "marks", "percentage", "score", "grade"]):
            for line in lines:
                m = re.search(r"(?:cgpa|gpa|grade|score)\s*[:=-]?\s*([0-9]+(?:\.[0-9]+)?(?:\s*/\s*10|\s*/\s*4|\s*%)?)", line, re.I)
                if m:
                    return m.group(1).strip()

        # Founding Year / Established
        if any(w in q_text for w in ["founding year", "founded", "established", "establishment"]):
            for line in lines:
                if any(k in line.lower() for k in ["founding year", "founded", "established", "establishment"]):
                    m = re.search(r"[:=-]\s*(.+)$", line)
                    if m:
                        val = m.group(1).strip()
                        yr = re.search(r"\b(18\d{2}|19\d{2}|20\d{2})\b", val)
                        return yr.group(0) if yr else val
                    yr = re.search(r"\b(18\d{2}|19\d{2}|20\d{2})\b", line)
                    if yr:
                        return yr.group(0)

        # ── 4. Structured Table Support ────────────────────────────────
        table_ans = _parse_table_data(lines, q_lower)
        if table_ans:
            return table_ans

        # ── 5. Structured Key-Value Matching ───────────────────────────
        best_kv_match = None
        best_kv_score = 0
        for line in lines:
            if ":" in line and not line.startswith(("http:", "https:")):
                key_part, val_part = line.split(":", 1)
                key_clean = normalize_text(key_part)
                key_words = set(key_clean.split())
                val_clean = val_part.strip()
                if key_words and val_clean:
                    matching_words = set(q_words) & key_words
                    if matching_words:
                        score = len(matching_words) / len(key_words)
                        if score > best_kv_score:
                            best_kv_score = score
                            best_kv_match = val_clean

        if best_kv_match and best_kv_score >= 0.5:
            return best_kv_match

        # ── 6. Universal Section-Aware Content Extraction ──────────────
        # Parse document into structured sections (Header -> Body lines)
        sections = _parse_sections(lines)

        best_section = None
        best_section_score = 0

        for sec in sections:
            header_norm = normalize_text(sec["header"])
            header_words = set(header_norm.split())
            if not header_words:
                continue

            # Check matching words between question and section header
            matched = set(q_words) & header_words
            if matched:
                score = len(matched) * 2.0 / (len(header_words) + 1)
                # Boost if exact keyword match
                if any(w in header_norm for w in q_words):
                    score += 1.0
                if score > best_section_score:
                    best_section_score = score
                    best_section = sec

        # If a matching section is found, extract its ACTUAL CONTENT (never just heading!)
        if best_section and best_section["body"]:
            body_lines = best_section["body"]
            sec_header = best_section["header"]

            is_narrative = (
                any(kw in sec_header.lower() for kw in ["objective", "policy", "summary", "overview", "abstract", "introduction", "conclusion", "what is", "about"])
                or any(q_lower.startswith(p) for p in ["what is", "define", "explain", "describe", "what are the course objectives", "what are the research objectives", "what is the leave policy"])
            )

            # Check if this section is a list / items / skills / benefits / features
            items = _extract_items_from_body(body_lines, sec_header)

            if not is_narrative and (any(_is_list_line(l) for l in body_lines) or any(kw in sec_header.lower() for kw in ["skill", "benefit", "perk", "tool", "language", "framework", "qualification", "competenc"])):
                if items:
                    return "\n".join(f"- {it}" for it in items)

            # If it's a narrative/paragraph section (e.g. Objectives, Policy, Summary, Conclusion)
            full_body_text = " ".join(body_lines).strip()
            if full_body_text:
                return deduplicate_sentences(full_body_text)
            elif items:
                return "\n".join(f"- {it}" for it in items)

        # ── 7. Concept / Definition Matching ───────────────────────────
        # E.g. "What is python?", "What is machine learning?", "What is the leave policy?"
        if q_lower.startswith("what is") or q_lower.startswith("define") or q_lower.startswith("explain") or q_lower.startswith("describe"):
            target_topic = re.sub(r"^(what is|what are|define|explain|describe)\s+(?:the\s+|a\s+|an\s+)?", "", q_lower).rstrip("?").strip()
            if target_topic:
                for line in lines:
                    line_lower = line.lower()
                    if target_topic in line_lower:
                        sentences = re.split(r"(?<=[.!?])\s+", line)
                        for s in sentences:
                            s_low = s.lower()
                            if target_topic in s_low and any(verb in s_low for verb in [" is ", " refers to ", " means ", " defined as ", " provides ", " allows ", " includes ", " receive "]):
                                return s.strip()
                        if len(line.split()) > 4 and not _is_heading(line):
                            return line.strip()

        # ── 8. Precise Fact / Sentence Matching ────────────────────────
        if q_words:
            best_sentence = None
            max_matched = 0
            for line in lines:
                if _is_heading(line):
                    continue  # NEVER return a heading line as a fact sentence
                sentences = re.split(r"(?<=[.!?])\s+", line)
                for sentence in sentences:
                    s_clean = normalize_text(sentence)
                    s_words = set(s_clean.split())
                    matched = len(set(q_words) & s_words)
                    if matched > max_matched and matched >= max(1, int(len(q_words) * 0.6)):
                        max_matched = matched
                        best_sentence = sentence.strip()

            if best_sentence:
                return deduplicate_sentences(best_sentence)

        # Fallback if no matching facts exist
        return FALLBACK_MSG

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        context_str = ""
        question_str = ""

        for m in messages:
            content_str = m.content if isinstance(m.content, str) else str(m.content)
            if "Context:" in content_str:
                parts = content_str.split("Context:", 1)
                if len(parts) > 1:
                    context_str = parts[1].strip()
            elif not isinstance(m, AIMessage) and content_str:
                question_str = content_str.strip()

        answer = self._extract_exact_answer(question_str, context_str)
        answer = deduplicate_sentences(answer)

        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=answer))])

    @property
    def _llm_type(self) -> str:
        return "local_grounded"


def get_llm():
    """Return an LLM instance configured for strict, zero-temperature precision."""
    provider = os.getenv("LLM_PROVIDER", "local").lower()

    if provider == "openai" and os.getenv("OPENAI_API_KEY"):
        from langchain_openai import ChatOpenAI
        model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        return ChatOpenAI(model=model, temperature=0.0, max_tokens=1024)
    elif provider == "openrouter" and os.getenv("OPENROUTER_API_KEY"):
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENROUTER_API_KEY")
        model = os.getenv("LLM_MODEL", "meta-llama/llama-3.2-1b-instruct:free")
        return ChatOpenAI(
            openai_api_key=api_key,
            openai_api_base="https://openrouter.ai/api/v1",
            model=model,
            temperature=0.0,
            max_tokens=1024,
        )
    elif provider == "ollama":
        from langchain_community.chat_models import ChatOllama
        model = os.getenv("LLM_MODEL", "llama3.2")
        base_url = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
        return ChatOllama(model=model, base_url=base_url, temperature=0.0)
    else:
        # Default local high-precision extractor
        return LocalGroundedChatModel()


def get_rag_chain(retriever: BaseRetriever):
    """
    Build and return the RAG retrieval chain with strict QA.
    """
    llm = get_llm()
    prompt = get_rag_prompt()

    # Combine documents into prompt context
    question_answer_chain = create_stuff_documents_chain(llm, prompt)

    # Wire retriever + QA chain
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)

    return rag_chain


