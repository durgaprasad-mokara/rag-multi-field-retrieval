"""
Chat API route — accepts a question, returns a RAG-powered answer, and persists history to PostgreSQL.
"""
import json
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ChatMessage
from app.schemas import ChatRequest, ChatResponse, ChatMessageResponse, SourceSnippet
from app.rag.chain import get_rag_chain
from app.rag.retriever import get_retriever

router = APIRouter(tags=["Chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Run a RAG query: retrieve relevant chunks, feed to the LLM,
    return the answer with source citations, and save exchange to PostgreSQL.
    """
    # Build retriever (optionally filtered by document_id)
    retriever = get_retriever(document_id=request.document_id)

    # Build and invoke the RAG chain
    chain = get_rag_chain(retriever)
    result = chain.invoke({"input": request.question})

    # Extract answer
    answer = result.get("answer", "I couldn't generate an answer.")

    # Extract source documents
    sources = []
    for doc in result.get("context", []):
        sources.append(
            SourceSnippet(
                document_name=doc.metadata.get("filename", "Unknown"),
                chunk_text=doc.page_content[:300],  # Truncate for display
                score=doc.metadata.get("score"),
            )
        )

    # Save chat history to PostgreSQL
    sources_json = json.dumps([s.model_dump() for s in sources])
    chat_record = ChatMessage(
        document_id=request.document_id,
        question=request.question,
        answer=answer,
        sources=sources_json,
    )
    db.add(chat_record)
    db.commit()

    return ChatResponse(answer=answer, sources=sources)


@router.get("/chat/history", response_model=list[ChatMessageResponse])
async def get_chat_history(document_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Retrieve saved chat message history from PostgreSQL."""
    query = db.query(ChatMessage)
    if document_id is not None:
        query = query.filter(ChatMessage.document_id == document_id)
    
    messages = query.order_by(ChatMessage.created_at.asc()).all()

    result = []
    for msg in messages:
        sources_list = []
        if msg.sources:
            try:
                raw_sources = json.loads(msg.sources)
                sources_list = [SourceSnippet(**s) for s in raw_sources]
            except Exception:
                pass
        result.append(
            ChatMessageResponse(
                id=msg.id,
                document_id=msg.document_id,
                question=msg.question,
                answer=msg.answer,
                sources=sources_list,
                created_at=msg.created_at,
            )
        )
    return result


@router.delete("/chat/history")
async def clear_chat_history(db: Session = Depends(get_db)):
    """Clear all chat history from PostgreSQL."""
    db.query(ChatMessage).delete()
    db.commit()
    return {"message": "Chat history cleared successfully"}

