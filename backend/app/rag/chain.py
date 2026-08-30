"""
RAG chain — composes retriever + prompt + LLM into a complete chain.
Supports Local Grounded Extractor (offline CPU), OpenAI, OpenRouter, and Ollama.
"""
import os
import re
from typing import Any, Optional
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.retrievers import BaseRetriever
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration

from app.rag.prompts import get_rag_prompt
from app.rag.deduplicator import deduplicate_sentences, normalize_text

FALLBACK_MSG = "Information not found in the selected document."


class LocalGroundedChatModel(BaseChatModel):
    """
    High-precision local document extractor.
    Extracts exact requested fields, answers direct questions, removes noise and duplicates,
    and returns 'Information not found in the uploaded document.' when information is absent.
    """

    def _extract_exact_answer(self, question: str, context: str) -> str:
        if not context or not context.strip():
            return FALLBACK_MSG

        q_clean = question.strip().lower()
        # Remove question punctuation
        q_text = re.sub(r"[?!.,]", "", q_clean).strip()
        
        # Stop words to ignore when extracting key concepts
        stopwords = {
            "what", "is", "the", "a", "an", "are", "were", "was", "of", "in", "for", 
            "to", "and", "or", "tell", "me", "give", "show", "who", "whom", "whose",
            "where", "when", "why", "how", "does", "did", "can", "could", "candidate",
            "candidates", "student", "students", "company", "companys", "document", "documents"
        }
        q_words = [w for w in q_text.split() if w not in stopwords and len(w) > 1]

        lines = [line.strip() for line in context.splitlines() if line.strip()]

        # Check if question specifies a distinct person/entity name not in context
        person_names_in_q = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", question)
        for pn in person_names_in_q:
            pn_lower = pn.lower()
            if not any(w in pn_lower for w in ["what", "where", "who", "when", "how", "why", "information", "candidate", "student", "employee", "company", "document"]):
                if pn_lower not in context.lower():
                    return FALLBACK_MSG

        # ── 1. Specific Entity Fast-Paths ───────────────────────────

        # Candidate / Student / Employee / Person Name
        if any(w in q_text for w in [
            "candidate name", "student name", "author name", "person name", 
            "candidate's name", "student's name", "employee name", "employee's name",
            "name of the employee", "name of the student", "name of the candidate",
            "who is the employee", "who is the candidate", "who is the student"
        ]):
            for line in lines:
                m = re.search(r"^(?:candidate\s+name|student\s+name|author\s+name|employee\s+name|employee\s+profile|student\s+profile|candidate\s+profile|employee|candidate|student|full\s+name|name)\s*[:=-]\s*(.+)$", line, re.I)
                if m:
                    return m.group(1).strip()
            # If resume/profile starts with a person name (2 to 3 words, capitalized, no company/document words)
            if lines and not lines[0].startswith("#") and ":" not in lines[0]:
                first_line = lines[0].strip()
                disallowed_words = [
                    "policy", "policies", "manual", "guide", "handbook", "protocol", "report",
                    "company", "inc", "corp", "ltd", "notes", "foundations", "document",
                    "documentation", "terms", "service", "agreement", "rules", "plan", "trial",
                    "university", "college", "school", "department", "curriculum", "resume", "cv"
                ]
                if not any(dw in first_line.lower() for dw in disallowed_words):
                    first_words = first_line.split()
                    if 2 <= len(first_words) <= 3 and all(w[0].isupper() for w in first_words if w.isalpha()):
                        return first_line
            return FALLBACK_MSG

        # General "What is the name / Name"
        if "name" in q_text:
            for line in lines:
                m = re.search(r"^(?:name|full\s+name|employee\s+profile|candidate\s+profile|student\s+profile)\s*[:=-]\s*(.+)$", line, re.I)
                if m:
                    return m.group(1).strip()

        # Phone Number
        if any(w in q_text for w in ["phone", "mobile", "contact number", "telephone", "cell"]):
            for line in lines:
                if any(k in line.lower() for k in ["phone", "mobile", "tel", "contact"]):
                    m = re.search(r"[:=-]\s*(.+)$", line)
                    if m:
                        return m.group(1).strip()
            phone_match = re.search(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,5}\)?[-.\s]?\d{3,5}[-.\s]?\d{3,5}", context)
            if phone_match and len(re.sub(r"\D", "", phone_match.group(0))) >= 7:
                return phone_match.group(0).strip()

        # Email
        if any(w in q_text for w in ["email", "e-mail", "mail"]):
            email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", context)
            if email_match:
                return email_match.group(0).strip()

        # CGPA / GPA / Marks
        if any(w in q_text for w in ["cgpa", "gpa", "marks", "percentage", "score", "grade"]):
            for line in lines:
                m = re.search(r"(?:cgpa|gpa|grade|score)\s*[:=-]?\s*([0-9]+(?:\.[0-9]+)?(?:\s*/\s*10|\s*/\s*4|\s*%)?)", line, re.I)
                if m:
                    return m.group(1).strip()

        # Founding Year / Founded
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

        # ── 2. Structured Key-Value Matching ────────────────────────
        # Checks if document has a "Key: Value" line matching question words
        best_kv_match = None
        best_kv_score = 0
        for line in lines:
            if ":" in line:
                key_part, val_part = line.split(":", 1)
                key_clean = normalize_text(key_part)
                key_words = set(key_clean.split())
                if key_words and val_part.strip():
                    matching_words = set(q_words) & key_words
                    if matching_words:
                        score = len(matching_words) / len(key_words)
                        if score > best_kv_score:
                            best_kv_score = score
                            best_kv_match = val_part.strip()

        if best_kv_match and best_kv_score >= 0.5:
            return best_kv_match

        # ── 3. Concept / Definition Matching ────────────────────────
        # E.g. "What is machine learning?"
        if q_clean.startswith("what is") or q_clean.startswith("define") or q_clean.startswith("explain"):
            target_topic = re.sub(r"^(what is|define|explain|describe)\s+", "", q_clean).rstrip("?").strip()
            if target_topic:
                for line in lines:
                    line_lower = line.lower()
                    if target_topic in line_lower:
                        # Extract definition sentence
                        sentences = re.split(r"(?<=[.!?])\s+", line)
                        for s in sentences:
                            if target_topic in s.lower() and any(verb in s.lower() for verb in [" is ", " refers to ", " means ", " defined as "]):
                                return s.strip()
                        if len(line.split()) > 4:
                            return line.strip()

        # ── 4. Precise Sentence Matching with Required Keyword Support ──
        if q_words:
            best_sentence = None
            max_matched = 0
            for line in lines:
                sentences = re.split(r"(?<=[.!?])\s+", line)
                for sentence in sentences:
                    s_clean = normalize_text(sentence)
                    s_words = set(s_clean.split())
                    matched = len(set(q_words) & s_words)
                    # All significant question terms or at least 70% must match
                    if matched > max_matched and matched >= max(1, int(len(q_words) * 0.7)):
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


