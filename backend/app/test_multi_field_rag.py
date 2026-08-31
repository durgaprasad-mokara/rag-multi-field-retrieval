"""
Automated acceptance tests for Multi-Field Query Decomposition, Retrieval, and Coverage.
"""
import requests
import io
from app.rag.multi_field import decompose_query, is_multi_field_query

BASE_URL = "http://localhost:8000"


def test_query_decomposition_logic():
    print("\n1. Testing Query Decomposition Logic...")

    q_multi = "Give me all skills, technical skills, education details, projects, professional summary, email, phone number, LinkedIn and GitHub."
    assert is_multi_field_query(q_multi) is True
    fields = decompose_query(q_multi)
    field_keys = [f.key for f in fields]
    
    expected_keys = ["skills", "technical_skills", "education", "projects", "professional_summary", "email", "phone", "linkedin", "github"]
    for k in expected_keys:
        assert k in field_keys, f"Missing expected field: {k}"
    print(f"   ✓ Decomposed 9 fields: {field_keys}")

    # Single-field query test
    q_single = "What are the skills?"
    assert is_multi_field_query(q_single) is False
    print("   ✓ Single-field query correctly identified as non-multi-field")

    # Another conversational multi-field phrasing
    q_multi_2 = "Skills means technology technical skills and education details and project section and professional summary and mail ID phone number and LinkedIn and GitHub."
    assert is_multi_field_query(q_multi_2) is True
    fields_2 = decompose_query(q_multi_2)
    field_keys_2 = [f.key for f in fields_2]
    for k in ["skills", "education", "projects", "email", "phone", "github"]:
        assert k in field_keys_2, f"Missing key in phrasing 2: {k}"
    print(f"   ✓ Phrasing 2 decomposed successfully: {field_keys_2}")


def test_multi_field_rag_acceptance():
    print("\n2. Testing End-to-End Multi-Field RAG QA...")

    # Fetch Category
    cats = requests.get(f"{BASE_URL}/api/categories").json()
    cat_resume = next((c for c in cats if "resume" in c["name"].lower()), cats[0])
    type_id = cat_resume["types"][0]["id"] if cat_resume.get("types") else 1

    resume_text = """Mokara Durga Prasad
Email: durga@example.com
Phone: +91 98765 43210
GitHub: https://github.com/durgaprasad-mokara

PROFESSIONAL SUMMARY:
Experienced Software Engineer specializing in scalable full-stack applications, distributed microservices, and AI-powered document intelligence systems.

TECHNICAL SKILLS:
- Python
- Java
- SQL
- React
- FastAPI
- Docker
- LangChain
- Qdrant

EDUCATION:
- B.Tech in Computer Science Engineering (2020 - 2024)
- Parul University
- CGPA: 8.9 / 10

PROJECTS:
- RAG Assistant: Enterprise multi-document intelligence engine with vector search and PostgreSQL.
- Cloud Platform: Microservices orchestration system using FastAPI and Docker.
"""

    file_payload = {"file": ("Candidate_Full_Profile.txt", io.BytesIO(resume_text.encode("utf-8")), "text/plain")}
    res_up = requests.post(f"{BASE_URL}/api/documents/upload", files=file_payload, data={"category_id": cat_resume["id"], "type_id": type_id})
    assert res_up.status_code == 200, f"Upload error: {res_up.text}"
    doc_id = res_up.json()["id"]

    # ── Test Acceptance Question ─────────────────────────────
    prompt_q = "Give me all skills, technical skills, education details, projects, professional summary, email, phone number, LinkedIn and GitHub."
    
    res = requests.post(
        f"{BASE_URL}/api/chat",
        json={"document_id": doc_id, "question": prompt_q, "target_response_time": 2.0},
    )
    assert res.status_code == 200, f"Chat error: {res.text}"
    answer = res.json()["answer"]
    print("\n--- MULTI-FIELD ANSWER OUTPUT ---")
    print(answer)
    print("---------------------------------\n")

    # Verify every requested field is present in answer
    assert "### Skills" in answer
    assert "Python" in answer or "Java" in answer
    assert "### Technical Skills" in answer
    assert "### Education" in answer
    assert "Parul University" in answer or "B.Tech" in answer
    assert "### Projects" in answer
    assert "RAG Assistant" in answer
    assert "### Professional Summary" in answer
    assert "Software Engineer" in answer
    assert "### Email" in answer
    assert "durga@example.com" in answer
    assert "### Phone" in answer
    assert "+91 98765 43210" in answer
    assert "### LinkedIn" in answer
    assert "Not available in the selected document." in answer
    assert "### GitHub" in answer
    assert "https://github.com/durgaprasad-mokara" in answer

    # Verify it DID NOT return only GitHub
    assert not answer.strip().startswith("https://github.com/")
    print("   ✓ Multi-field query returned all 9 fields with 100% complete coverage!")

    # ── Test Single-Field Question ───────────────────────────
    print("\n3. Testing Single-Field Query Constraint...")
    res_single = requests.post(
        f"{BASE_URL}/api/chat",
        json={"document_id": doc_id, "question": "What is the phone number?", "target_response_time": 2.0},
    )
    assert res_single.status_code == 200
    single_ans = res_single.json()["answer"]
    print(f"   Phone Answer: '{single_ans}'")
    assert "+91 98765 43210" in single_ans
    assert "Education" not in single_ans
    assert "Projects" not in single_ans
    assert "GitHub" not in single_ans
    print("   ✓ Single-field query returned only the requested field without unrequested additions")


if __name__ == "__main__":
    print("==================================================================")
    print("🚀 RUNNING MULTI-FIELD RAG ACCEPTANCE TEST SUITE")
    print("==================================================================")
    test_query_decomposition_logic()
    test_multi_field_rag_acceptance()
    print("\n==================================================================")
    print("🎉 ALL MULTI-FIELD ACCEPTANCE TESTS PASSED PERFECTLY!")
    print("==================================================================")
