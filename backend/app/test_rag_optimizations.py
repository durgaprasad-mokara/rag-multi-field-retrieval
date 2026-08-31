"""
Automated test suite for RAG Document Cleaning, Smart Chunking, Token Reduction, and Response-Time Metrics.
"""
import requests
import io
import time
from app.rag.cleaner import clean_extracted_text, deduplicate_paragraphs
from app.rag.chunker import split_documents, _get_document_strategy
from app.rag.retriever import compress_retrieved_context
from langchain_core.documents import Document

BASE_URL = "http://localhost:8000"


def test_text_cleaning():
    print("\n1. Testing Text Cleaning & Normalization...")
    
    # Test 1: Excessive spaces within lines
    dirty_1 = "Python    is   a programming    language."
    cleaned_1 = clean_extracted_text(dirty_1)
    assert cleaned_1 == "Python is a programming language.", f"Failed: {cleaned_1}"
    print("   ✓ Excessive whitespace normalization passed")

    # Test 2: OCR repeated commas and double dots
    dirty_2 = "Machine Learning,,,, is powerful.. and scalable."
    cleaned_2 = clean_extracted_text(dirty_2)
    assert cleaned_2 == "Machine Learning, is powerful. and scalable.", f"Failed: {cleaned_2}"
    print("   ✓ OCR punctuation noise cleaning passed")

    # Test 3: Duplicated line-start names
    dirty_3 = "John Smith John Smith\nSoftware Engineer"
    cleaned_3 = clean_extracted_text(dirty_3)
    assert "John Smith" in cleaned_3 and "John Smith John Smith" not in cleaned_3, f"Failed: {cleaned_3}"
    print("   ✓ Duplicated name artifact normalization passed")

    # Test 4: Preserves table formatting and markdown
    table_text = "| Skill | Level |\n| Python | Expert |\n| SQL | Advanced |"
    cleaned_table = clean_extracted_text(table_text)
    assert "| Skill | Level |" in cleaned_table and "| Python | Expert |" in cleaned_table
    print("   ✓ Markdown table structure preservation passed")

    # Test 5: Paragraph deduplication
    dup_p = "Python is an interpreted language.\n\nPython is an interpreted language.\n\nJavaScript is used for frontend."
    deduped = deduplicate_paragraphs(dup_p)
    assert deduped.count("Python is an interpreted language.") == 1
    assert "JavaScript is used for frontend." in deduped
    print("   ✓ Paragraph deduplication passed")


def test_smart_chunking():
    print("\n2. Testing Smart & Document-Type-Aware Chunking...")
    
    assert _get_document_strategy("Resume / CV", "Developer Resume", "resume.pdf") == "resume"
    assert _get_document_strategy("Company", "Company Policies", "policy.docx") == "policy"
    assert _get_document_strategy("Research", "Clinical Trials", "paper.pdf") == "research"
    print("   ✓ Strategy detection passed")

    doc = Document(
        page_content="TECHNICAL SKILLS\nPython, FastAPI, SQL, React\n\nEXPERIENCE\nSenior Developer at Acme Corp",
        metadata={"source": "test.txt", "page": 0},
    )
    chunks = split_documents(
        [doc],
        document_id=999,
        filename="test.txt",
        category_name="Resume / CV",
        type_name="Developer Resume",
    )
    assert len(chunks) >= 1
    c0 = chunks[0]
    assert c0.metadata["document_id"] == 999
    assert c0.metadata["category_name"] == "Resume / CV"
    assert c0.metadata["strategy"] == "resume"
    assert c0.metadata["source_reference"] == "test.txt (p. 1)"
    print("   ✓ Enriched chunk metadata passed")


def test_context_compression():
    print("\n3. Testing Context Compression & Token Budgeting...")
    
    docs = [
        Document(page_content="Python is a programming language. Python is a programming language.", metadata={}),
        Document(page_content="Python is a programming language.", metadata={}),
        Document(page_content="FastAPI is a modern web framework.", metadata={}),
    ]
    compressed = compress_retrieved_context(docs, max_token_chars=500)
    assert len(compressed) <= 2
    print("   ✓ Context compression and sentence deduplication passed")


def test_end_to_end_rag_with_targets():
    print("\n4. Testing End-to-End Chat with Response Time Targets...")
    
    # Fetch categories
    cats = requests.get(f"{BASE_URL}/api/categories").json()
    cat_resume = next((c for c in cats if "resume" in c["name"].lower()), cats[0])
    type_id = cat_resume["types"][0]["id"] if cat_resume.get("types") else 1

    # Upload test document
    content = """Mokara Durga Prasad
Email: durga@example.com
Phone: +91 98765 43210
TECHNICAL SKILLS:
- Python
- FastAPI
- LangChain
- PostgreSQL
- Qdrant
- React.js

WORK EXPERIENCE:
Software Engineer at Cloud Innovations Inc. (2022 - Present)
"""
    file_payload = {"file": ("Resume_Perf_Test.txt", io.BytesIO(content.encode("utf-8")), "text/plain")}
    res_up = requests.post(f"{BASE_URL}/api/documents/upload", files=file_payload, data={"category_id": cat_resume["id"], "type_id": type_id})
    assert res_up.status_code == 200, f"Upload error: {res_up.text}"
    doc_id = res_up.json()["id"]

    # Query with target_response_time = 0.5s (FAST)
    res_fast = requests.post(
        f"{BASE_URL}/api/chat",
        json={"document_id": doc_id, "question": "What are the skills?", "target_response_time": 0.5},
    )
    assert res_fast.status_code == 200
    data_fast = res_fast.json()
    assert "Python" in data_fast["answer"]
    assert "response_time_ms" in data_fast
    assert data_fast["target_response_time_ms"] == 500.0
    print(f"   ✓ Fast mode query returned in {data_fast['response_time_ms']}ms (Target: {data_fast['target_response_time_ms']}ms)")

    # Query with target_response_time = 2.0s (BALANCED)
    res_bal = requests.post(
        f"{BASE_URL}/api/chat",
        json={"document_id": doc_id, "question": "What is the phone number?", "target_response_time": 2.0},
    )
    assert res_bal.status_code == 200
    data_bal = res_bal.json()
    assert "+91 98765 43210" in data_bal["answer"]
    assert data_bal["target_response_time_ms"] == 2000.0
    print(f"   ✓ Balanced mode query returned in {data_bal['response_time_ms']}ms (Within target: {data_bal['within_target']})")


if __name__ == "__main__":
    print("==================================================================")
    print("🚀 RUNNING RAG OPTIMIZATION & RESPONSE TIME TEST SUITE")
    print("==================================================================")
    test_text_cleaning()
    test_smart_chunking()
    test_context_compression()
    test_end_to_end_rag_with_targets()
    print("\n==================================================================")
    print("🎉 ALL RAG OPTIMIZATION TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================================")
