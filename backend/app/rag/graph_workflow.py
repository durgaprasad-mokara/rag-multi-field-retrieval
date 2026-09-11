"""
LangGraph RAG Workflow — orchestrates the complete RAG pipeline with AI/ML intelligence.

Wraps EXISTING LangChain components (retriever, LLM, multi_field, deduplicator)
into a stateful LangGraph workflow with AI/ML classification, routing, and scoring.

Architecture:
    classify_query → detect_intent → route_query → detect_fields → retrieve_qdrant
    → score_relevance → [expand_and_retry] → deduplicate_chunks → extract_fields
    → generate_answer → validate_answer → [retrieve_missing_fields] → score_confidence
    → finalize_response
"""
import logging
import time
from typing import Any, Dict

from langgraph.graph import StateGraph, END

from app.rag.graph_state import RAGGraphState
from app.rag.intelligence import (
    classify_query as ml_classify_query,
    detect_intent as ml_detect_intent,
    route_query as ml_route_query,
    score_retrieval_relevance as ml_score_relevance,
    estimate_answer_confidence as ml_estimate_confidence,
    expand_query as ml_expand_query,
)

logger = logging.getLogger(__name__)

FALLBACK_MSG = "This answer is not available in the selected document. Please ask a question related to the available content."
ERROR_MSG = "An error occurred while processing your request. Please try again."


# ══════════════════════════════════════════════════════════════
# NODE FUNCTIONS — each wraps existing LangChain components
# ══════════════════════════════════════════════════════════════

def _update_timings(state: dict, node_name: str, elapsed_ms: float) -> dict:
    """Merge a new timing entry into the existing timings dict."""
    timings = dict(state.get("timings") or {})
    timings[f"{node_name}_ms"] = elapsed_ms
    return timings


def node_classify_query(state: RAGGraphState) -> dict:
    """AI/ML: Classify the user's question type."""
    t0 = time.perf_counter()
    try:
        query_type = ml_classify_query(state["user_question"])
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        logger.info(f"[classify_query] type={query_type} ({elapsed}ms)")
        return {
            "query_type": query_type,
            "timings": _update_timings(state, "classify_query", elapsed),
        }
    except Exception as e:
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        logger.error(f"[classify_query] failed: {e}", exc_info=True)
        return {
            "query_type": "factual_lookup",
            "timings": _update_timings(state, "classify_query", elapsed),
        }


def node_detect_intent(state: RAGGraphState) -> dict:
    """AI/ML: Detect the user's intent."""
    t0 = time.perf_counter()
    try:
        intent = ml_detect_intent(state["user_question"], state.get("query_type", "factual_lookup"))
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        logger.info(f"[detect_intent] intent={intent} ({elapsed}ms)")
        return {
            "detected_intent": intent,
            "timings": _update_timings(state, "detect_intent", elapsed),
        }
    except Exception as e:
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        logger.error(f"[detect_intent] failed: {e}", exc_info=True)
        return {
            "detected_intent": "general",
            "timings": _update_timings(state, "detect_intent", elapsed),
        }


def node_route_query(state: RAGGraphState) -> dict:
    """AI/ML: Determine retrieval strategy."""
    t0 = time.perf_counter()
    try:
        field_count = len(state.get("requested_fields") or [])
        routing = ml_route_query(
            state.get("query_type", "factual_lookup"),
            state.get("detected_intent", "general"),
            field_count,
            state.get("target_response_time", 2.0),
        )
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        logger.info(f"[route_query] strategy={routing['strategy']} k={routing['k']} ({elapsed}ms)")
        return {
            "routing_strategy": routing["strategy"],
            "routing_config": routing,
            "timings": _update_timings(state, "route_query", elapsed),
        }
    except Exception as e:
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        logger.error(f"[route_query] failed: {e}", exc_info=True)
        return {
            "routing_strategy": "targeted",
            "routing_config": {"strategy": "targeted", "k": 5, "max_chars": 4500},
            "timings": _update_timings(state, "route_query", elapsed),
        }


def node_detect_fields(state: RAGGraphState) -> dict:
    """Detect requested fields using EXISTING multi_field.decompose_query()."""
    t0 = time.perf_counter()
    try:
        from app.rag.multi_field import decompose_query
        fields = decompose_query(state["user_question"])
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        field_keys = [f.key for f in fields]
        logger.info(f"[detect_fields] fields={field_keys} ({elapsed}ms)")
        return {
            "requested_fields": fields,
            "timings": _update_timings(state, "detect_fields", elapsed),
        }
    except Exception as e:
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        logger.error(f"[detect_fields] failed: {e}", exc_info=True)
        return {
            "requested_fields": [],
            "error": f"Technical error in detect_fields: {str(e)}",
            "timings": _update_timings(state, "detect_fields", elapsed),
        }


def node_retrieve_qdrant(state: RAGGraphState) -> dict:
    """Retrieve chunks using EXISTING retriever with document filtering."""
    t0 = time.perf_counter()
    try:
        from app.rag.retriever import get_retriever
        from app.rag.deduplicator import normalize_text

        doc_ids = state.get("document_ids") or []
        routing_config = state.get("routing_config") or {"k": 5, "max_chars": 4500}
        target_rt = state.get("target_response_time", 2.0)
        fields = state.get("requested_fields") or []

        retriever = get_retriever(
            document_ids=doc_ids if doc_ids else None,
            target_response_time=target_rt,
        )

        all_chunks = []
        seen_chunks = set()

        if len(fields) >= 1 and state.get("routing_strategy") == "field_level":
            # Multi-field: field-level retrieval
            for field in fields:
                enhanced_query = field.sub_query + " " + " ".join(field.retrieval_keywords)
                original_k = retriever.base_retriever.search_kwargs.get("k", 5)
                retriever.base_retriever.search_kwargs["k"] = routing_config.get("k", 15)
                sub_chunks = retriever.invoke(enhanced_query)
                retriever.base_retriever.search_kwargs["k"] = original_k

                for c in sub_chunks:
                    norm_c = normalize_text(c.page_content[:200])
                    if norm_c not in seen_chunks:
                        seen_chunks.add(norm_c)
                        all_chunks.append(c)
        else:
            # Single query retrieval
            retriever.base_retriever.search_kwargs["k"] = routing_config.get("k", 5)
            all_chunks = retriever.invoke(state["user_question"])

        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        logger.info(f"[retrieve_qdrant] chunks={len(all_chunks)} ({elapsed}ms)")
        return {
            "retrieved_chunks": all_chunks,
            "timings": _update_timings(state, "retrieve_qdrant", elapsed),
        }
    except Exception as e:
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        logger.error(f"[retrieve_qdrant] failed: {e}", exc_info=True)
        return {
            "retrieved_chunks": [],
            "error": f"Technical error in retrieve_qdrant: {str(e)}",
            "timings": _update_timings(state, "retrieve_qdrant", elapsed),
        }


def node_score_relevance(state: RAGGraphState) -> dict:
    """AI/ML: Score retrieved chunks for relevance (annotate, never remove)."""
    t0 = time.perf_counter()
    try:
        chunks = state.get("retrieved_chunks") or []
        if not chunks:
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            return {
                "retrieved_chunks": chunks,
                "retrieval_confidence": "insufficient",
                "timings": _update_timings(state, "score_relevance", elapsed),
            }

        # Try to use embeddings for scoring
        embeddings_model = None
        try:
            from app.rag.embeddings import get_embeddings
            embeddings_model = get_embeddings()
        except Exception:
            pass

        scored_chunks, confidence = ml_score_relevance(
            state["user_question"], chunks, embeddings_model
        )

        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        logger.info(f"[score_relevance] confidence={confidence} ({elapsed}ms)")
        return {
            "retrieved_chunks": scored_chunks,
            "retrieval_confidence": confidence,
            "timings": _update_timings(state, "score_relevance", elapsed),
        }
    except Exception as e:
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        logger.error(f"[score_relevance] failed: {e}", exc_info=True)
        return {
            "retrieval_confidence": "medium",
            "timings": _update_timings(state, "score_relevance", elapsed),
        }


def node_expand_and_retry(state: RAGGraphState) -> dict:
    """AI/ML: Expand query and retry retrieval when confidence is low."""
    t0 = time.perf_counter()
    try:
        from app.rag.retriever import get_retriever
        from app.rag.deduplicator import normalize_text

        expansion_terms = ml_expand_query(
            state["user_question"],
            state.get("detected_intent", "general"),
            state.get("requested_fields"),
        )

        if not expansion_terms:
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            return {
                "query_expansion_terms": [],
                "retry_count": state.get("retry_count", 0) + 1,
                "timings": _update_timings(state, "expand_and_retry", elapsed),
            }

        # Retrieve with expanded terms
        doc_ids = state.get("document_ids") or []
        retriever = get_retriever(
            document_ids=doc_ids if doc_ids else None,
            target_response_time=state.get("target_response_time", 2.0),
        )

        existing_chunks = list(state.get("retrieved_chunks") or [])
        seen = {normalize_text(c.page_content[:200]) for c in existing_chunks}

        expanded_query = state["user_question"] + " " + " ".join(expansion_terms[:5])
        retriever.base_retriever.search_kwargs["k"] = 10
        new_chunks = retriever.invoke(expanded_query)

        for c in new_chunks:
            norm_c = normalize_text(c.page_content[:200])
            if norm_c not in seen:
                seen.add(norm_c)
                existing_chunks.append(c)

        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        logger.info(f"[expand_and_retry] expansion_terms={len(expansion_terms)} new_total={len(existing_chunks)} ({elapsed}ms)")
        return {
            "retrieved_chunks": existing_chunks,
            "query_expansion_terms": expansion_terms,
            "retry_count": state.get("retry_count", 0) + 1,
            "timings": _update_timings(state, "expand_and_retry", elapsed),
        }
    except Exception as e:
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        logger.error(f"[expand_and_retry] failed: {e}", exc_info=True)
        return {
            "retry_count": state.get("retry_count", 0) + 1,
            "timings": _update_timings(state, "expand_and_retry", elapsed),
        }


def node_deduplicate_chunks(state: RAGGraphState) -> dict:
    """Deduplicate chunks using EXISTING deduplicator."""
    t0 = time.perf_counter()
    try:
        from app.rag.deduplicator import deduplicate_documents
        from app.rag.retriever import compress_retrieved_context

        chunks = state.get("retrieved_chunks") or []
        routing_config = state.get("routing_config") or {"max_chars": 4500}
        max_chars = routing_config.get("max_chars", 4500)

        deduped = deduplicate_documents(chunks, similarity_threshold=0.85)
        compressed = compress_retrieved_context(deduped, max_token_chars=max_chars)

        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        logger.info(f"[deduplicate_chunks] {len(chunks)}→{len(compressed)} ({elapsed}ms)")
        return {
            "deduplicated_chunks": compressed,
            "timings": _update_timings(state, "deduplicate_chunks", elapsed),
        }
    except Exception as e:
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        logger.error(f"[deduplicate_chunks] failed: {e}", exc_info=True)
        return {
            "deduplicated_chunks": state.get("retrieved_chunks") or [],
            "timings": _update_timings(state, "deduplicate_chunks", elapsed),
        }


def node_extract_fields(state: RAGGraphState) -> dict:
    """Extract field values using EXISTING multi_field + chain extraction."""
    t0 = time.perf_counter()
    try:
        from app.rag.multi_field import extract_field_from_text, NOT_AVAILABLE_MSG
        from app.rag.chain import LocalGroundedChatModel

        fields = state.get("requested_fields") or []
        chunks = state.get("deduplicated_chunks") or state.get("retrieved_chunks") or []
        local_extractor = LocalGroundedChatModel()

        if not fields:
            # No specific fields detected — this is a single question
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            return {
                "field_results": [],
                "timings": _update_timings(state, "extract_fields", elapsed),
            }

        context_str = "\n\n".join(c.page_content for c in chunks)
        field_results = []

        for field in fields:
            # Build field-specific context from chunks that mention field keywords
            field_context_parts = []
            for c in chunks:
                content_lower = c.page_content.lower()
                if any(kw in content_lower for kw in field.retrieval_keywords):
                    field_context_parts.append(c.page_content)

            # If no field-specific chunks, use all context
            field_context = "\n\n".join(field_context_parts) if field_context_parts else context_str

            ans = extract_field_from_text(field, field_context, local_extractor=local_extractor)

            # Fallback: if not found in field context, try full context
            if ans == NOT_AVAILABLE_MSG and field_context != context_str:
                ans = extract_field_from_text(field, context_str, local_extractor=local_extractor)

            field_results.append((field, ans))

        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        logger.info(f"[extract_fields] extracted={len(field_results)} ({elapsed}ms)")
        return {
            "field_results": field_results,
            "timings": _update_timings(state, "extract_fields", elapsed),
        }
    except Exception as e:
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        logger.error(f"[extract_fields] failed: {e}", exc_info=True)
        return {
            "field_results": [],
            "error": f"Technical error in extract_fields: {str(e)}",
            "timings": _update_timings(state, "extract_fields", elapsed),
        }


def node_generate_answer(state: RAGGraphState) -> dict:
    """Generate the final answer using EXISTING chain / multi_field formatter."""
    t0 = time.perf_counter()
    try:
        from app.rag.multi_field import format_multi_field_response, NOT_AVAILABLE_MSG
        from app.rag.chain import get_rag_chain, get_llm, LocalGroundedChatModel
        from app.rag.deduplicator import deduplicate_sentences
        from app.rag.retriever import get_retriever

        fields = state.get("requested_fields") or []
        field_results = state.get("field_results") or []
        chunks = state.get("deduplicated_chunks") or state.get("retrieved_chunks") or []

        if field_results:
            # Multi-field: use existing format_multi_field_response
            answer = format_multi_field_response(field_results)

            # Track which fields were actually answered
            answered = []
            missing = []
            for field, ans in field_results:
                if ans and ans != NOT_AVAILABLE_MSG and "not available" not in ans.lower():
                    answered.append(field.key)
                else:
                    missing.append(field)

            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            return {
                "generated_answer": answer,
                "answered_fields": answered,
                "missing_fields": missing,
                "timings": _update_timings(state, "generate_answer", elapsed),
            }
        else:
            # Single question: use existing RAG chain
            doc_ids = state.get("document_ids") or []
            retriever = get_retriever(
                document_ids=doc_ids if doc_ids else None,
                target_response_time=state.get("target_response_time", 2.0),
            )
            chain = get_rag_chain(retriever)
            result = chain.invoke({"input": state["user_question"]})

            answer = result.get("answer", "")
            answer = deduplicate_sentences(answer)

            # Store context from chain result for source extraction
            chain_context = result.get("context", [])
            if chain_context and not chunks:
                chunks = chain_context

            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            return {
                "generated_answer": answer,
                "answered_fields": [],
                "missing_fields": [],
                "deduplicated_chunks": chunks if chunks else chain_context,
                "timings": _update_timings(state, "generate_answer", elapsed),
            }
    except Exception as e:
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        logger.error(f"[generate_answer] failed: {e}", exc_info=True)
        return {
            "generated_answer": "",
            "error": f"Technical error in generate_answer: {str(e)}",
            "timings": _update_timings(state, "generate_answer", elapsed),
        }


def node_validate_answer(state: RAGGraphState) -> dict:
    """Validate the answer — check field coverage and answer quality."""
    t0 = time.perf_counter()
    try:
        from app.rag.multi_field import NOT_AVAILABLE_MSG

        answer = state.get("generated_answer", "")
        fields = state.get("requested_fields") or []
        field_results = state.get("field_results") or []
        missing = state.get("missing_fields") or []

        # For single questions: basic validation
        if not fields:
            is_valid = bool(answer and answer.strip() and answer != FALLBACK_MSG)
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            return {
                "validation_passed": is_valid,
                "timings": _update_timings(state, "validate_answer", elapsed),
            }

        # For multi-field: check coverage
        answered = state.get("answered_fields") or []
        still_missing = []

        for field in fields:
            if field.key not in answered:
                still_missing.append(field)

        validation_passed = len(still_missing) == 0

        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        logger.info(f"[validate_answer] passed={validation_passed} answered={len(answered)}/{len(fields)} ({elapsed}ms)")
        return {
            "validation_passed": validation_passed,
            "missing_fields": still_missing,
            "timings": _update_timings(state, "validate_answer", elapsed),
        }
    except Exception as e:
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        logger.error(f"[validate_answer] failed: {e}", exc_info=True)
        return {
            "validation_passed": True,  # Don't block on validation errors
            "timings": _update_timings(state, "validate_answer", elapsed),
        }


def node_retrieve_missing_fields(state: RAGGraphState) -> dict:
    """Targeted retrieval for missing fields, then re-extract."""
    t0 = time.perf_counter()
    try:
        from app.rag.retriever import get_retriever
        from app.rag.multi_field import extract_field_from_text, NOT_AVAILABLE_MSG
        from app.rag.chain import LocalGroundedChatModel
        from app.rag.deduplicator import normalize_text

        missing = state.get("missing_fields") or []
        if not missing:
            elapsed = round((time.perf_counter() - t0) * 1000, 2)
            return {
                "retry_count": state.get("retry_count", 0) + 1,
                "timings": _update_timings(state, "retrieve_missing_fields", elapsed),
            }

        doc_ids = state.get("document_ids") or []
        retriever = get_retriever(
            document_ids=doc_ids if doc_ids else None,
            target_response_time=state.get("target_response_time", 2.0),
        )
        local_extractor = LocalGroundedChatModel()

        # Get existing field results and chunks
        field_results = list(state.get("field_results") or [])
        existing_chunks = list(state.get("deduplicated_chunks") or state.get("retrieved_chunks") or [])
        seen = {normalize_text(c.page_content[:200]) for c in existing_chunks}

        updated_field_results = []
        newly_answered = list(state.get("answered_fields") or [])
        still_missing = []

        for field in state.get("requested_fields") or []:
            # Check if this field was already answered
            existing_ans = None
            for f, a in field_results:
                if f.key == field.key:
                    existing_ans = a
                    break

            if existing_ans and existing_ans != NOT_AVAILABLE_MSG and "not available" not in existing_ans.lower():
                updated_field_results.append((field, existing_ans))
                continue

            # Try targeted retrieval for this missing field
            enhanced_query = field.sub_query + " " + " ".join(field.retrieval_keywords)
            retriever.base_retriever.search_kwargs["k"] = 15
            new_chunks = retriever.invoke(enhanced_query)

            for c in new_chunks:
                norm_c = normalize_text(c.page_content[:200])
                if norm_c not in seen:
                    seen.add(norm_c)
                    existing_chunks.append(c)

            # Try extraction from new + existing context
            all_context = "\n\n".join(c.page_content for c in existing_chunks)
            ans = extract_field_from_text(field, all_context, local_extractor=local_extractor)

            updated_field_results.append((field, ans))
            if ans and ans != NOT_AVAILABLE_MSG and "not available" not in ans.lower():
                if field.key not in newly_answered:
                    newly_answered.append(field.key)
            else:
                still_missing.append(field)

        # Regenerate answer with updated results
        from app.rag.multi_field import format_multi_field_response
        updated_answer = format_multi_field_response(updated_field_results)

        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        logger.info(f"[retrieve_missing_fields] recovered={len(newly_answered) - len(state.get('answered_fields', []))} still_missing={len(still_missing)} ({elapsed}ms)")
        return {
            "field_results": updated_field_results,
            "generated_answer": updated_answer,
            "answered_fields": newly_answered,
            "missing_fields": still_missing,
            "deduplicated_chunks": existing_chunks,
            "retry_count": state.get("retry_count", 0) + 1,
            "timings": _update_timings(state, "retrieve_missing_fields", elapsed),
        }
    except Exception as e:
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        logger.error(f"[retrieve_missing_fields] failed: {e}", exc_info=True)
        return {
            "retry_count": state.get("retry_count", 0) + 1,
            "timings": _update_timings(state, "retrieve_missing_fields", elapsed),
        }


def node_score_confidence(state: RAGGraphState) -> dict:
    """AI/ML: Estimate overall answer confidence."""
    t0 = time.perf_counter()
    try:
        confidence = ml_estimate_confidence(
            state.get("requested_fields") or [],
            state.get("answered_fields") or [],
            state.get("retrieval_confidence", "medium"),
            state.get("validation_passed", True),
        )
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        logger.info(f"[score_confidence] confidence={confidence} ({elapsed}ms)")
        return {
            "answer_confidence": confidence,
            "timings": _update_timings(state, "score_confidence", elapsed),
        }
    except Exception as e:
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        logger.error(f"[score_confidence] failed: {e}", exc_info=True)
        return {
            "answer_confidence": "medium",
            "timings": _update_timings(state, "score_confidence", elapsed),
        }


def node_finalize_response(state: RAGGraphState) -> dict:
    """Assemble the final response with metadata, sources, and timings."""
    t0 = time.perf_counter()
    try:
        answer = state.get("generated_answer", "")
        error = state.get("error", "")

        # Distinguish technical errors from missing information
        if error and not answer:
            answer = ERROR_MSG
            logger.error(f"[finalize_response] returning error response: {error}")
        elif not answer or not answer.strip():
            answer = FALLBACK_MSG

        # Build context list for backward compatibility
        context = state.get("deduplicated_chunks") or state.get("retrieved_chunks") or []

        # Build AI/ML metadata for diagnostics
        ai_ml_metadata = {
            "query_type": state.get("query_type", "unknown"),
            "detected_intent": state.get("detected_intent", "unknown"),
            "routing_strategy": state.get("routing_strategy", "unknown"),
            "retrieval_confidence": state.get("retrieval_confidence", "unknown"),
            "answer_confidence": state.get("answer_confidence", "unknown"),
            "fields_requested": len(state.get("requested_fields") or []),
            "fields_answered": len(state.get("answered_fields") or []),
            "fields_missing": len(state.get("missing_fields") or []),
            "retries": state.get("retry_count", 0),
            "query_expansion_terms": state.get("query_expansion_terms") or [],
            "validation_passed": state.get("validation_passed", True),
        }

        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        timings = _update_timings(state, "finalize_response", elapsed)

        return {
            "answer": answer,
            "context": context,
            "ai_ml_metadata": ai_ml_metadata,
            "timings": timings,
        }
    except Exception as e:
        logger.error(f"[finalize_response] failed: {e}", exc_info=True)
        return {
            "answer": ERROR_MSG,
            "context": [],
            "ai_ml_metadata": {},
            "timings": state.get("timings") or {},
        }


# ══════════════════════════════════════════════════════════════
# CONDITIONAL EDGE FUNCTIONS
# ══════════════════════════════════════════════════════════════

def should_expand_query(state: RAGGraphState) -> str:
    """After score_relevance: decide whether to expand query or continue."""
    confidence = state.get("retrieval_confidence", "medium")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    if confidence in ("low", "insufficient") and retry_count < max_retries:
        return "expand_and_retry"
    return "deduplicate_chunks"


def should_retry_missing(state: RAGGraphState) -> str:
    """After validate_answer: decide whether to retry missing fields."""
    missing = state.get("missing_fields") or []
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    if missing and retry_count < max_retries:
        return "retrieve_missing_fields"
    return "score_confidence"


# ══════════════════════════════════════════════════════════════
# GRAPH CONSTRUCTION
# ══════════════════════════════════════════════════════════════

def build_rag_graph() -> StateGraph:
    """Build and compile the LangGraph RAG workflow."""
    graph = StateGraph(RAGGraphState)

    # ── Add nodes ─────────────────────────────────────────────
    graph.add_node("classify_query", node_classify_query)
    graph.add_node("detect_intent", node_detect_intent)
    graph.add_node("detect_fields", node_detect_fields)
    graph.add_node("route_query", node_route_query)
    graph.add_node("retrieve_qdrant", node_retrieve_qdrant)
    graph.add_node("score_relevance", node_score_relevance)
    graph.add_node("expand_and_retry", node_expand_and_retry)
    graph.add_node("deduplicate_chunks", node_deduplicate_chunks)
    graph.add_node("extract_fields", node_extract_fields)
    graph.add_node("generate_answer", node_generate_answer)
    graph.add_node("validate_answer", node_validate_answer)
    graph.add_node("retrieve_missing_fields", node_retrieve_missing_fields)
    graph.add_node("score_confidence", node_score_confidence)
    graph.add_node("finalize_response", node_finalize_response)

    # ── Set entry point ───────────────────────────────────────
    graph.set_entry_point("classify_query")

    # ── Linear edges ──────────────────────────────────────────
    graph.add_edge("classify_query", "detect_intent")
    graph.add_edge("detect_intent", "detect_fields")
    graph.add_edge("detect_fields", "route_query")
    graph.add_edge("route_query", "retrieve_qdrant")
    graph.add_edge("retrieve_qdrant", "score_relevance")

    # ── Conditional: after scoring relevance ───────────────────
    graph.add_conditional_edges(
        "score_relevance",
        should_expand_query,
        {
            "expand_and_retry": "expand_and_retry",
            "deduplicate_chunks": "deduplicate_chunks",
        },
    )
    graph.add_edge("expand_and_retry", "deduplicate_chunks")

    # ── Continue pipeline ─────────────────────────────────────
    graph.add_edge("deduplicate_chunks", "extract_fields")
    graph.add_edge("extract_fields", "generate_answer")
    graph.add_edge("generate_answer", "validate_answer")

    # ── Conditional: after validation ─────────────────────────
    graph.add_conditional_edges(
        "validate_answer",
        should_retry_missing,
        {
            "retrieve_missing_fields": "retrieve_missing_fields",
            "score_confidence": "score_confidence",
        },
    )
    graph.add_edge("retrieve_missing_fields", "validate_answer")

    # ── Final steps ───────────────────────────────────────────
    graph.add_edge("score_confidence", "finalize_response")
    graph.add_edge("finalize_response", END)

    return graph.compile()


# ══════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════

# Compile the graph once at module level for reuse
_compiled_graph = None


def _get_graph():
    """Get or build the compiled graph (lazy singleton)."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_rag_graph()
    return _compiled_graph


def run_rag_graph(
    question: str,
    document_ids: list = None,
    target_response_time: float = 2.0,
    document_name: str = "",
    session_id: str = "",
    category_id: str = "",
    type_id: str = "",
    voice_enabled: bool = False,
) -> Dict[str, Any]:
    """
    Execute the LangGraph RAG workflow with AI/ML intelligence.

    Returns a dict compatible with the existing execute_rag_query() output:
        {"answer": str, "context": list[Document], "ai_ml_metadata": dict, "timings": dict}
    """
    graph = _get_graph()

    # Prepare document_ids as string list for Qdrant filtering
    doc_ids_str = []
    if document_ids:
        doc_ids_str = [str(d) for d in document_ids if d is not None]

    initial_state: RAGGraphState = {
        "user_question": question,
        "session_id": session_id,
        "document_id": doc_ids_str[0] if doc_ids_str else "",
        "document_ids": doc_ids_str,
        "document_name": document_name,
        "category_id": category_id,
        "type_id": type_id,
        "target_response_time": target_response_time,
        "voice_enabled": voice_enabled,
        "retry_count": 0,
        "max_retries": 2,
        "error": "",
        "timings": {},
    }

    # Execute the graph
    result = graph.invoke(initial_state)

    return {
        "answer": result.get("answer", FALLBACK_MSG),
        "context": result.get("context", []),
        "ai_ml_metadata": result.get("ai_ml_metadata", {}),
        "timings": result.get("timings", {}),
    }
