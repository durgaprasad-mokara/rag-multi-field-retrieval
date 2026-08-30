"""
End-to-end automated verification script for Universal Document RAG Assistant.
"""
import requests
import io
import time

BASE_URL = "http://localhost:8000"

def test_full_pipeline():
    print("=== 🧪 Running RAG Pipeline Verification ===")

    # 1. Upload Resume
    resume_content = """Durga Prasad
Email: durga.prasad@example.com
Phone: +91 98765 43210
Education: B.Tech in Computer Science, CGPA: 8.7
Skills: Python, FastAPI, LangChain, SQL, React.js
Experience: Software Engineer at Acme Corp from 2021 to Present.
"""
    resume_file = ("resume.txt", io.BytesIO(resume_content.encode("utf-8")), "text/plain")
    res = requests.post(f"{BASE_URL}/api/upload", files={"file": resume_file})
    assert res.status_code == 200, f"Upload failed: {res.text}"
    doc_resume = res.json()
    doc_resume_id = doc_resume["id"]
    print(f"✅ Uploaded Resume (ID={doc_resume_id})")

    # 2. Upload Company Document
    company_content = """Acme Innovations Inc.
Founding Year: 2018
Headquarters: San Francisco, California
Founders: Alice Smith and Bob Johnson
Total Employees: 150
Annual Revenue: $25 Million
Mission: Empowering developers with cutting-edge AI tools.
"""
    company_file = ("company_profile.txt", io.BytesIO(company_content.encode("utf-8")), "text/plain")
    res = requests.post(f"{BASE_URL}/api/upload", files={"file": company_file})
    assert res.status_code == 200, f"Upload failed: {res.text}"
    doc_company = res.json()
    doc_company_id = doc_company["id"]
    print(f"✅ Uploaded Company Profile (ID={doc_company_id})")

    # 3. Upload Study Material
    study_content = """Machine Learning Basics
Machine learning is a subset of artificial intelligence focused on building applications that learn from data and improve their accuracy over time without being explicitly programmed.
Supervised learning uses labeled datasets to train algorithms.
Unsupervised learning uses unlabeled data to discover hidden patterns.
"""
    study_file = ("study_notes.md", io.BytesIO(study_content.encode("utf-8")), "text/markdown")
    res = requests.post(f"{BASE_URL}/api/upload", files={"file": study_file})
    assert res.status_code == 200, f"Upload failed: {res.text}"
    doc_study = res.json()
    doc_study_id = doc_study["id"]
    print(f"✅ Uploaded Study Notes (ID={doc_study_id})")

    time.sleep(1)

    # ── Test Queries ──────────────────────────────────────────
    test_cases = [
        # Candidate questions
        (doc_resume_id, "What is the candidate's name?", "Durga Prasad"),
        (doc_resume_id, "What is the phone number?", "+91 98765 43210"),
        (doc_resume_id, "What is the student's CGPA?", "8.7"),
        (doc_resume_id, "What are the skills?", "Python, FastAPI, LangChain, SQL, React.js"),
        (doc_resume_id, "What is the driver license number?", "Information not found in the uploaded document."),

        # Company questions
        (doc_company_id, "What is the company's founding year?", "2018"),
        (doc_company_id, "What is the annual revenue?", "$25 Million"),
        (doc_company_id, "Who is the CEO?", "Information not found in the uploaded document."),

        # Study material questions
        (doc_study_id, "What is machine learning?", "learn from data"),
        (doc_study_id, "What is quantum computing?", "Information not found in the uploaded document."),

        # Cross-document isolation check: Ask company question targeting Resume doc
        (doc_resume_id, "What is the company's founding year?", "Information not found in the uploaded document."),
    ]

    print("\n--- 🔍 Testing Exact Question-Answering ---")
    all_passed = True
    for doc_id, question, expected_substr in test_cases:
        res = requests.post(f"{BASE_URL}/api/chat", json={"question": question, "document_id": doc_id})
        assert res.status_code == 200, f"Chat request failed: {res.text}"
        data = res.json()
        answer = data["answer"].strip()
        
        passed = expected_substr.lower() in answer.lower()
        status_icon = "✅" if passed else "❌"
        print(f"{status_icon} Q: '{question}' (Doc ID: {doc_id})")
        print(f"   A: '{answer}'")
        if not passed:
            print(f"   ⚠️ Expected substring: '{expected_substr}'")
            all_passed = False

    if all_passed:
        print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")
    else:
        print("\n⚠️ SOME TESTS FAILED")

if __name__ == "__main__":
    test_full_pipeline()
