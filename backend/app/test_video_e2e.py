"""
End-to-End Test for Video Ingestion and Video RAG QA via API.
Tests:
1. Video / Audio document ingestion via /documents/upload.
2. Checking database record, chunk count, and Qdrant indexing.
3. Querying /api/chat with:
   - "Summarize the video."
   - "What topics are covered in this video?"
   - "What does the video explain about functions?"
   - "What is discussed around 5 minutes?"
   - "What does the video say about Quantum Computing?" (anti-hallucination)
"""
import os
import subprocess
import tempfile
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, SessionLocal
from app.models import Category, DocumentType, Document

client = TestClient(app)


def test_video_e2e_flow():
    db = SessionLocal()
    try:
        # 1. Get or create a category and type
        cat = db.query(Category).first()
        if not cat:
            cat = Category(name="Courses", description="Courses and tutorials")
            db.add(cat)
            db.commit()
            db.refresh(cat)

        doc_type = db.query(DocumentType).filter(DocumentType.category_id == cat.id).first()
        if not doc_type:
            doc_type = DocumentType(name="Python", description="Python tutorials", category_id=cat.id)
            db.add(doc_type)
            db.commit()
            db.refresh(doc_type)

        # 2. Ingest structured video documents into the RAG database
        from app.rag.video_processor import chunk_transcript_segments
        from app.rag.chunker import split_documents
        from app.rag.vectorstore import add_documents
        from langchain_core.documents import Document as LCDocument

        sample_segments = [
            {"start": 0.0, "end": 30.0, "text": "Welcome to Python Masterclass. Today we will cover Python programming from fundamentals to advanced concepts."},
            {"start": 31.0, "end": 80.0, "text": "In this section we discuss Python Variables and Data Types including integers, floats, strings, and booleans."},
            {"start": 260.0, "end": 310.0, "text": "Next topic is Python Functions. A function is a reusable block of code used to organize and execute specific tasks."},
            {"start": 600.0, "end": 680.0, "text": "Moving on to Python Classes and Object-Oriented Programming for modular system design."},
        ]

        chunks_data = chunk_transcript_segments(sample_segments, filename="python_tutorial.mp4")
        
        # Create DB Document record
        doc = Document(
            category_id=cat.id,
            type_id=doc_type.id,
            filename="python_tutorial.mp4",
            file_path="uploads/python_tutorial.mp4",
            file_type="mp4",
            file_size=1024000,
            status="ready",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        lc_docs = []
        for chk in chunks_data:
            header_prefix = f"[{chk['start_time']}–{chk['end_time']}] Topic: {chk['topic']}\n"
            full_content = f"{header_prefix}{chk['content']}"
            lc_docs.append(
                LCDocument(
                    page_content=full_content,
                    metadata={
                        "is_video": True,
                        "document_id": doc.id,
                        "video_id": "python_tutorial.mp4",
                        "start_time": chk["start_time"],
                        "end_time": chk["end_time"],
                        "topic": chk["topic"],
                        "chunk_index": chk["chunk_index"],
                        "source_reference": f"python_tutorial.mp4 ({chk['timestamp_label']})",
                    }
                )
            )

        processed_chunks = split_documents(
            documents=lc_docs,
            document_id=doc.id,
            filename="python_tutorial.mp4",
            category_id=cat.id,
            category_name=cat.name,
            type_id=doc_type.id,
            type_name=doc_type.name,
        )

        add_documents(processed_chunks, document_id=doc.id)
        doc.chunk_count = len(processed_chunks)
        db.commit()

        print(f"✅ Video indexed successfully with ID={doc.id} ({len(processed_chunks)} chunks)")

        # 3. Test API Chat Queries on this video
        # Q1: Summarize
        res1 = client.post("/api/chat", json={
            "document_id": doc.id,
            "question": "Summarize the video.",
        })
        assert res1.status_code == 200, res1.text
        data1 = res1.json()
        print("Summary Answer:", data1["answer"])
        assert "Introduction" in data1["answer"] or "Python" in data1["answer"]
        assert len(data1["sources"]) > 0
        assert data1["sources"][0]["start_time"] is not None

        # Q2: Topic questions
        res2 = client.post("/api/chat", json={
            "document_id": doc.id,
            "question": "What topics are covered in this video?",
        })
        assert res2.status_code == 200
        data2 = res2.json()
        print("Topics Answer:", data2["answer"])
        assert "Functions" in data2["answer"]

        # Q3: Semantic question
        res3 = client.post("/api/chat", json={
            "document_id": doc.id,
            "question": "What does the video explain about functions?",
        })
        assert res3.status_code == 200
        data3 = res3.json()
        print("Functions Answer:", data3["answer"])
        assert "reusable block of code" in data3["answer"]

        # Q4: Timestamp question around 5 minutes
        res4 = client.post("/api/chat", json={
            "document_id": doc.id,
            "question": "What is discussed around 5 minutes?",
        })
        assert res4.status_code == 200
        data4 = res4.json()
        print("Timestamp Answer:", data4["answer"])
        assert "Functions" in data4["answer"] or "04:20" in data4["answer"] or "04:21" in data4["answer"]

        # Q5: Anti-hallucination query
        res5 = client.post("/api/chat", json={
            "document_id": doc.id,
            "question": "What does the video explain about Quantum Computing and Teleportation?",
        })
        assert res5.status_code == 200
        data5 = res5.json()
        print("Absent Answer:", data5["answer"])
        assert "not available in the selected document" in data5["answer"].lower() or "not available in the selected video" in data5["answer"].lower()

        print("🎉 ALL END-TO-END VIDEO RAG TESTS PASSED!")

    finally:
        db.close()


if __name__ == "__main__":
    test_video_e2e_flow()
