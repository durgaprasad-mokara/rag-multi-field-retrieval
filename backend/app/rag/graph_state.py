"""
LangGraph State Definition — Typed state object for the RAG workflow.
Contains all information flowing between LangGraph nodes.
"""
from typing import TypedDict, Any


class RAGGraphState(TypedDict, total=False):
    """Complete state for the LangGraph RAG workflow.

    All fields are optional (total=False) so nodes only update
    the fields they are responsible for.
    """

    # ── Input ────────────────────────────────────────────────
    user_question: str
    session_id: str
    document_id: str
    document_ids: list
    document_name: str
    category_id: str
    type_id: str
    target_response_time: float
    voice_enabled: bool

    # ── AI/ML Intelligence ───────────────────────────────────
    query_type: str              # factual_lookup | multi_field | summary | comparison | analytical | conversational | unsupported
    detected_intent: str         # skills | education | contact | projects | general | etc.
    routing_strategy: str        # targeted | field_level | broad | expanded | fallback
    routing_config: dict         # {"k": int, "max_chars": int}
    retrieval_confidence: str    # high | medium | low | insufficient
    answer_confidence: str       # high | medium | low | insufficient
    query_expansion_terms: list  # additional search terms if expansion is triggered

    # ── RAG Pipeline ─────────────────────────────────────────
    requested_fields: list       # List[FieldDefinition] from existing multi_field.py
    retrieved_chunks: list       # List[Document] from Qdrant
    deduplicated_chunks: list    # List[Document] after dedup
    field_results: list          # List[tuple(FieldDefinition, str)] — extracted answers per field
    generated_answer: str        # Final answer text
    answered_fields: list        # List[str] — field keys that received real answers
    missing_fields: list         # List[FieldDefinition] — fields not yet answered

    # ── Control Flow ─────────────────────────────────────────
    retry_count: int             # Current retry iteration (starts at 0)
    max_retries: int             # Safe retry limit (default: 2)
    validation_passed: bool      # Whether answer passed validation
    error: str                   # Error message if any (empty string = no error)

    # ── Output ───────────────────────────────────────────────
    context: list                # List[Document] — for backward compat with execute_rag_query
    answer: str                  # Final answer (alias for generated_answer, for compat)
    sources: list                # List[dict] — source snippets
    chart_data: dict             # Chart JSON if applicable
    timings: dict                # Per-node timing measurements {"node_name_ms": float}
    total_time_ms: float         # Total workflow time
    ai_ml_metadata: dict         # Classification + intent + confidence for diagnostics/tracing
