from app.database import SessionLocal
from app.rag.retriever import get_retriever
from uuid import UUID

def test_retriever():
    db = SessionLocal()
    try:
        doc_id = UUID("6ac4ba08-a33b-45a5-b86e-d9bae8bead27")
        retriever = get_retriever(document_ids=[doc_id], k=5)
        docs = retriever.invoke("What is the email address or mail ID? email mail @ gmail outlook contact")
        print("Number of docs:", len(docs))
        for d in docs:
            print(d.page_content[:50])
            print("---")
    finally:
        db.close()

test_retriever()
