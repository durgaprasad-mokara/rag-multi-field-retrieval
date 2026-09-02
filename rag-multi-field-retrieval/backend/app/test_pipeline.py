"""
End-to-end automated verification script for Universal Document RAG Assistant.
"""
import requests
import io
import time

BASE_URL = "http://localhost:8000"

def test_full_pipeline():
    print("=== 🧪 Running RAG Pipeline Verification ===")

    # Fetch categories
    cats = requests.get(f"{BASE_URL}/api/categories").json()
    cat_resume = next((c for c in cats if "resume" in c["name"].lower() or "student" in c["name"].lower()), cats[0])
    cat_company = next((c for c in cats if "company" in c["name"].lower() or "business" in c["name"].lower()), cats[0])
    cat_study = next((c for c in cats if "study" in c["name"].lower() or "education" in c["name"].lower()), cats[0])

    type_resume_id = cat_resume["types"][0]["id"] if cat_resume.get("types") else 1
    type_company_id = cat_company["types"][0]["id"] if cat_company.get("types") else 1
    type_study_id = cat_study["types"][0]["id"] if cat_study.get("types") else 1

    # 1. Upload Resume
    resume_content = """Durga Prasad
Email: durga.prasad@example.com
Phone: +91 98765 43210
Education: B.Tech in Computer Science, CGPA: 8.7
Skills: Python, FastAPI, LangChain, SQL, React.js
Experience: Software Engineer at Acme Corp from 2021 to Present.
"""
    resume_file = {"file": ("resume.txt", io.BytesIO(resume_content.encode("utf-8")), "text/plain")}
    res = requests.post(f"{BASE_URL}/api/documents/upload", files=resume_file, data={"category_id": cat_resume["id"], "type_id": type_resume_id})
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
    company_file = {"file": ("company_profile.txt", io.BytesIO(company_content.encode("utf-8")), "text/plain")}
    res = requests.post(f"{BASE_URL}/api/documents/upload", files=company_file, data={"category_id": cat_company["id"], "type_id": type_company_id})
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
    study_file = {"file": ("study_notes.md", io.BytesIO(study_content.encode("utf-8")), "text/markdown")}
    res = requests.post(f"{BASE_URL}/api/documents/upload", files=study_file, data={"category_id": cat_study["id"], "type_id": type_study_id})
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
        (doc_resume_id, "What is the driver license number?", "This answer is not available in the selected document."),

        # Company questions
        (doc_company_id, "What is the company's founding year?", "2018"),
        (doc_company_id, "What is the annual revenue?", "$25 Million"),
        (doc_company_id, "Who is the CEO?", "This answer is not available in the selected document."),

        # Study material questions
        (doc_study_id, "What is machine learning?", "learn from data"),
        (doc_study_id, "What is quantum computing?", "This answer is not available in the selected document."),

        # Cross-document isolation check: Ask company question targeting Resume doc
        (doc_resume_id, "What is the company's founding year?", "This answer is not available in the selected document."),
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
