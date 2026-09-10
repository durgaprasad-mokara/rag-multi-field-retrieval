from app.database import SessionLocal
from app.schemas import ChatRequest
from app.api.chat import chat
import asyncio
from uuid import UUID

async def test():
    db = SessionLocal()
    try:
        doc_id = UUID("6ac4ba08-a33b-45a5-b86e-d9bae8bead27")
        queries = [
            "What is my phone number?",
            "What is my email?",
            "What are my skills?",
            "Give me my skills, projects, and education",
            "What is my cgpa?",
            "What is my linkedin profile?",
            "What is my github?",
            "What is my professional summary?",
        ]
        for q in queries:
            print(f"--- Q: {q} ---")
            req = ChatRequest(document_id=doc_id, question=q)
            res = await chat(req, db)
            print("Answer:\n", res.answer)
            print()
    finally:
        db.close()

asyncio.run(test())
