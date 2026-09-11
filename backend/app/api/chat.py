"""
Chat API route — strictly document-locked RAG sessions and high-precision question answering.
"""
import json
import re
import time
import uuid
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app.models import ChatMessage, ChatSession, Document, ChartOutput
from app.schemas import (
    ChatRequest,
    ChatResponse,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionResponse,
    ChatSessionDetailResponse,
    ChatMessageItem,
    SourceSnippet,
)
from app.rag.chain import get_rag_chain, execute_rag_query, execute_rag_query_with_graph, FALLBACK_MSG
from app.rag.retriever import get_retriever
from app.rag.deduplicator import deduplicate_sentences, normalize_text

router = APIRouter(prefix="/chat", tags=["Chat & Sessions"])

DOC_FALLBACK_MSG = "This answer is not available in the selected document. Please ask a question related to the available content."


def _clean_final_answer(answer: str, question: Optional[str] = None) -> str:
    """Clean and standardize the final answer string."""
    if not answer or not answer.strip():
        return DOC_FALLBACK_MSG

    # If it is a multi-field structured answer with ### headers, preserve the structured output
    if answer.strip().startswith("### ") or "\n### " in answer:
        return answer.strip()

    # Strip prefixes if any model outputted them
    answer = re.sub(r"^(?:Answer|Exact Answer|Response|Output)\s*:\s*", "", answer, flags=re.I).strip()
    answer = re.sub(r"^Based on (?:the|your) (?:uploaded |selected )?document[s]?\s*[:,]?\s*", "", answer, flags=re.I).strip()

    # Strip echoed question if model repeated it
    if question:
        q_strip = question.strip().rstrip("?!.").lower()
        if answer.lower().startswith(q_strip):
            answer = answer[len(q_strip):].lstrip("?:!.- \n\t").strip()
    
    # Check for missing info patterns in single-field answers
    missing_patterns = [
        "not found in the",
        "i don't have enough information",
        "couldn't find specific relevant information",
        "not mentioned in the document",
        "information is not available",
        "not available in the selected document",
        "this answer is not available",
        "this information is not available",
        "i don't know",
        "maybe",
    ]
    if any(p in answer.lower() for p in missing_patterns):
        return DOC_FALLBACK_MSG

    return deduplicate_sentences(answer)


# ── Chat Session Management ───────────────────────────────────

@router.post("/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
def create_chat_session(session_in: ChatSessionCreate, db: Session = Depends(get_db)):
    """Create a new chat session locked to a specific document."""
    doc = db.query(Document).filter(Document.id == session_in.document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    session_id = str(uuid.uuid4())
    session_title = session_in.title or f"Chat with {doc.filename}"

    session = ChatSession(
        id=session_id,
        selected_document_id=doc.id,
        selected_category_id=doc.category_id,
        selected_type_id=doc.type_id,
        session_name=session_title,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    cat_name = doc.category.name if doc.category else None
    type_name = doc.doc_type.name if doc.doc_type else None

    return ChatSessionResponse(
        id=str(session.id),
        document_id=doc.id,
        document_name=doc.filename,
        category_id=doc.category_id,
        category_name=cat_name,
        type_id=doc.type_id,
        type_name=type_name,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=0,
    )


@router.get("/sessions", response_model=List[ChatSessionResponse])
def get_chat_sessions(document_id: Optional[UUID] = None, db: Session = Depends(get_db)):
    """List chat sessions, optionally filtered by document_id."""
    query = db.query(ChatSession)
    if document_id is not None:
        query = query.filter(ChatSession.document_id == document_id)

    sessions = query.order_by(ChatSession.updated_at.desc()).all()
    results = []

    for s in sessions:
        doc_name = s.document.filename if s.document else "Unknown Document"
        cat_name = s.document.category.name if s.document and s.document.category else None
        type_name = s.document.doc_type.name if s.document and s.document.doc_type else None
        msg_count = len(s.messages)

        results.append(
            ChatSessionResponse(
                id=s.id,
                document_id=s.document_id,
                document_name=doc_name,
                category_id=s.category_id,
                category_name=cat_name,
                type_id=s.type_id,
                type_name=type_name,
                title=s.title,
                created_at=s.created_at,
                updated_at=s.updated_at,
                message_count=msg_count,
            )
        )
    return results


@router.get("/sessions/{session_id}", response_model=ChatSessionDetailResponse)
def get_chat_session(session_id: str, db: Session = Depends(get_db)):
    """Get chat session details and message history."""
    s = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    doc_name = s.document.filename if s.document else "Unknown Document"
    cat_name = s.document.category.name if s.document and s.document.category else None
    type_name = s.document.doc_type.name if s.document and s.document.doc_type else None

    msg_items = []
    for msg in s.messages:
        sources_list = []
        resp_ms = None
        tgt_ms = None
        within_tgt = None
        if msg.sources:
            try:
                raw = json.loads(msg.sources)
                if isinstance(raw, dict):
                    snippets = raw.get("snippets", [])
                    resp_ms = raw.get("response_time_ms")
                    tgt_ms = raw.get("target_response_time_ms")
                    within_tgt = raw.get("within_target")
                    sources_list = [SourceSnippet(**src) for src in snippets]
                elif isinstance(raw, list):
                    sources_list = [SourceSnippet(**src) for src in raw]
            except Exception:
                pass
        
        chart_data_dict = None
        if getattr(msg, "chart", None) and msg.chart.chart_json:
            try:
                chart_data_dict = json.loads(msg.chart.chart_json)
            except Exception:
                pass

        msg_items.append(
            ChatMessageItem(
                id=msg.id,
                role=msg.role,
                question=msg.question,
                answer=msg.answer,
                sources=sources_list,
                chart=chart_data_dict,
                created_at=msg.created_at,
            )
        )

    return ChatSessionDetailResponse(
        id=s.id,
        document_id=s.document_id,
        document_name=doc_name,
        category_id=s.category_id,
        category_name=cat_name,
        type_id=s.type_id,
        type_name=type_name,
        title=s.title,
        created_at=s.created_at,
        updated_at=s.updated_at,
        message_count=len(msg_items),
        messages=msg_items,
    )


@router.delete("/sessions/{session_id}")
def delete_chat_session(session_id: str, db: Session = Depends(get_db)):
    """Delete a chat session and its messages."""
    s = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Chat session not found.")

    db.delete(s)
    db.commit()
    return {"message": "Chat session deleted successfully."}


# ── Chat Execution ────────────────────────────────────────────

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Run a high-precision, document-locked RAG query:
    1. Resolve active session and its locked document_id.
    2. Retrieve relevant, deduplicated chunks ONLY from the locked document.
    3. Extract exact answer using zero-temperature LLM / high-precision parser.
    4. Save exchange to PostgreSQL session history.
    """
    # ── 1. Resolve Session & Document Scope ──────────────────
    session = None
    target_doc_ids = []
    primary_doc_name = "Selected Documents"
    primary_doc_id = None

    if request.session_id:
        session = db.query(ChatSession).filter(ChatSession.id == request.session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="Invalid session_id. Chat session not found.")
        primary_doc_id = session.document_id
        if primary_doc_id:
            target_doc_ids = [primary_doc_id]
            doc = db.query(Document).filter(Document.id == primary_doc_id).first()
            if doc:
                primary_doc_name = doc.filename
    elif request.document_ids and len(request.document_ids) > 0:
        target_doc_ids = request.document_ids
        primary_doc_id = target_doc_ids[0]
        first_doc = db.query(Document).filter(Document.id == primary_doc_id).first()
        if first_doc:
            primary_doc_name = f"{first_doc.filename} (+{len(target_doc_ids)-1} more)" if len(target_doc_ids) > 1 else first_doc.filename
        session = ChatSession(
            id=str(uuid.uuid4()),
            selected_document_id=primary_doc_id,
            selected_category_id=first_doc.category_id if first_doc else None,
            selected_type_id=first_doc.type_id if first_doc else None,
            session_name=f"Chat with {primary_doc_name}",
        )
        db.add(session)
        db.commit()
        db.refresh(session)
    elif request.document_id:
        primary_doc_id = request.document_id
        target_doc_ids = [primary_doc_id]
        doc = db.query(Document).filter(Document.id == primary_doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found.")
        primary_doc_name = doc.filename
        
        session = db.query(ChatSession).filter(ChatSession.selected_document_id == doc.id).order_by(ChatSession.updated_at.desc()).first()
        if not session:
            session = ChatSession(
                id=str(uuid.uuid4()),
                selected_document_id=doc.id,
                selected_category_id=doc.category_id,
                selected_type_id=doc.type_id,
                session_name=f"Chat with {doc.filename}",
            )
            db.add(session)
            db.commit()
            db.refresh(session)
    else:
        raise HTTPException(
            status_code=400,
            detail="A document must be selected to start a chat. Please provide session_id or document_id.",
        )

    # ── 2. Build & Execute Document-Specific RAG Pipeline ────
    t_start = time.perf_counter()
    result = execute_rag_query_with_graph(
        question=request.question,
        target_doc_ids=target_doc_ids,
        target_response_time=request.target_response_time,
        document_name=primary_doc_name,
        session_id=str(session.id) if session else "",
        category_id=str(session.category_id) if session and session.category_id else "",
        type_id=str(session.type_id) if session and session.type_id else "",
    )
    t_end = time.perf_counter()

    # ── 3. Extract & Clean Answer ────────────────────────────
    raw_answer = result.get("answer", "")
    answer = _clean_final_answer(raw_answer, request.question)

    # ── 3.5 Extract Chart JSON if present ─────────────────────
    chart_data_dict = None
    if "CHART_JSON_START" in answer and "CHART_JSON_END" in answer:
        try:
            start_idx = answer.find("CHART_JSON_START") + len("CHART_JSON_START")
            end_idx = answer.find("CHART_JSON_END")
            chart_json_str = answer[start_idx:end_idx].strip()
            chart_data_dict = json.loads(chart_json_str)
            # Remove the JSON payload and markers from the readable answer
            answer = answer[:answer.find("CHART_JSON_START")].strip()
        except Exception:
            pass

    # ── 5. Extract & Deduplicate Source Documents ────────────
    sources: list[SourceSnippet] = []
    seen_sources = set()

    for d in result.get("context", []):
        text_snippet = d.page_content[:300].strip()
        norm_snippet = normalize_text(text_snippet)
        if norm_snippet and norm_snippet not in seen_sources:
            seen_sources.add(norm_snippet)
            sources.append(
                SourceSnippet(
                    document_name=d.metadata.get("filename", primary_doc_name),
                    chunk_text=text_snippet,
                    page_number=d.metadata.get("page_number"),
                    start_time=d.metadata.get("start_time"),
                    end_time=d.metadata.get("end_time"),
                    topic=d.metadata.get("topic") or d.metadata.get("section"),
                    score=d.metadata.get("score"),
                )
            )

    # ── 6. Compute Latency Metrics ───────────────────────────
    total_ms = round((t_end - t_start) * 1000, 2)
    target_sec = request.target_response_time if request.target_response_time else 2.0
    target_ms = round(target_sec * 1000, 2)
    within_target = total_ms <= target_ms

    metrics = {
        "total_ms": total_ms,
        "target_ms": target_ms,
        "within_target": within_target,
        "ai_ml": result.get("ai_ml_metadata", {}),
    }

    # ── 7. Save Message to PostgreSQL Session History ─────────
    sources_payload = {
        "snippets": [s.model_dump() for s in sources],
        "response_time_ms": total_ms,
        "target_response_time_ms": target_ms,
        "within_target": within_target,
    }
    sources_json = json.dumps(sources_payload)
    
    user_msg = ChatMessage(
        session_id=session.id,
        document_id=primary_doc_id,
        role="user",
        content=request.question,
        input_type="text",
    )
    # Save Assistant message
    assistant_msg = ChatMessage(
        session_id=session.id,
        document_id=primary_doc_id,
        role="assistant",
        content=answer,
        retrieval_metadata={"sources_json": sources_json} if sources_json else {},
    )
    db.add(user_msg)
    db.add(assistant_msg)
    
    # Update session timestamp
    session.updated_at = func.now()
    db.commit()
    db.refresh(assistant_msg)

    # ── 8. Save Chart Data to PostgreSQL ──────────────────────
    if chart_data_dict and primary_doc_id:
        chart_out = ChartOutput(
            chat_message_id=assistant_msg.id,
            document_id=primary_doc_id,
            chart_json=json.dumps(chart_data_dict)
        )
        db.add(chart_out)
        db.commit()

    return ChatResponse(
        session_id=str(session.id),
        document_id=primary_doc_id,
        document_name=primary_doc_name,
        answer=answer,
        sources=sources,
        chart=chart_data_dict,
        response_time_ms=total_ms,
        target_response_time_ms=target_ms,
        within_target=within_target,
        metrics=metrics,
    )


@router.get("/history", response_model=list[ChatMessageResponse])
def get_chat_history(
    session_id: Optional[str] = None,
    document_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
):
    """Retrieve saved chat message history from PostgreSQL."""
    query = db.query(ChatMessage)
    if session_id:
        query = query.filter(ChatMessage.session_id == session_id)
    elif document_id is not None:
        query = query.filter(ChatMessage.document_id == document_id)

    messages = query.order_by(ChatMessage.created_at.asc()).all()

    result = []
    for msg in messages:
        sources_list = []
        resp_ms = None
        tgt_ms = None
        within_tgt = None
        if msg.sources:
            try:
                raw = json.loads(msg.sources)
                if isinstance(raw, dict):
                    snippets = raw.get("snippets", [])
                    resp_ms = raw.get("response_time_ms")
                    tgt_ms = raw.get("target_response_time_ms")
                    within_tgt = raw.get("within_target")
                    sources_list = [SourceSnippet(**s) for s in snippets]
                elif isinstance(raw, list):
                    sources_list = [SourceSnippet(**s) for s in raw]
            except Exception:
                pass
        
        chart_data_dict = None
        if getattr(msg, "chart", None) and msg.chart.chart_json:
            try:
                chart_data_dict = json.loads(msg.chart.chart_json)
            except Exception:
                pass

        result.append(
            ChatMessageResponse(
                id=msg.id,
                session_id=msg.session_id,
                document_id=msg.document_id,
                role=msg.role,
                question=msg.question,
                answer=msg.answer,
                sources=sources_list,
                chart=chart_data_dict,
                response_time_ms=resp_ms,
                target_response_time_ms=tgt_ms,
                within_target=within_tgt,
                created_at=msg.created_at,
            )
        )
    return result


@router.delete("/history")
def clear_chat_history(
    session_id: Optional[str] = None,
    document_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
):
    """Clear chat message history for a session or document."""
    query = db.query(ChatMessage)
    if session_id:
        query = query.filter(ChatMessage.session_id == session_id)
    elif document_id is not None:
        query = query.filter(ChatMessage.document_id == document_id)

    deleted_count = query.delete(synchronize_session=False)
    db.commit()
    return {"message": f"Deleted {deleted_count} messages from history."}
