"""
Comprehensive integration test suite for the Multi-Category, Multi-Type, Document-Specific RAG Chatbot.
"""
import requests
import io
import time

BASE_URL = "http://localhost:8000"

def run_suite():
    print("==================================================")
    print("🧪 UNIVERSAL RAG CHATBOT FULL INTEGRATION SUITE")
    print("==================================================")

    # ── 1. Category Management ──────────────────────────────
    print("\n1. Testing Category & Type Management CRUD...")
    
    # Create Custom Category: "Healthcare" (or fetch if existing)
    res = requests.post(f"{BASE_URL}/api/categories", json={"name": "Healthcare", "description": "Medical & Hospital Documents"})
    if res.status_code == 201:
        health_cat = res.json()
        print(f"✅ Created Category: {health_cat['name']} (ID={health_cat['id']})")
    else:
        res = requests.get(f"{BASE_URL}/api/categories")
        all_c = res.json()
        health_cat = next(c for c in all_c if c["name"] == "Healthcare")
        print(f"✅ Found Category: {health_cat['name']} (ID={health_cat['id']})")

    # Create Custom Type under Healthcare: "Clinical Trials" (or fetch if existing)
    res = requests.post(f"{BASE_URL}/api/categories/{health_cat['id']}/types", json={"name": "Clinical Trials", "description": "Trial protocols and outcome reports"})
    if res.status_code == 201:
        trial_type = res.json()
        print(f"✅ Created Type: {trial_type['name']} (ID={trial_type['id']}) under Healthcare")
    else:
        res = requests.get(f"{BASE_URL}/api/categories/{health_cat['id']}/types")
        all_t = res.json()
        trial_type = next(t for t in all_t if t["name"] == "Clinical Trials")
        print(f"✅ Found Type: {trial_type['name']} (ID={trial_type['id']}) under Healthcare")

    # Fetch Categories and verify Healthcare is listed
    res = requests.get(f"{BASE_URL}/api/categories")
    assert res.status_code == 200
    all_cats = res.json()
    cat_lookup = {c["name"]: c for c in all_cats}
    if "Students" in cat_lookup:
        cat_lookup["Student"] = cat_lookup["Students"]
    assert "Healthcare" in cat_lookup
    assert "Company" in cat_lookup
    assert "Education" in cat_lookup
    assert "Student" in cat_lookup

    # ── 2. Ingesting Documents Across Domains ────────────────
    print("\n2. Ingesting Multi-Domain Documents...")
    
    # Doc A: Student Profile / Resume (Student > Student Profile)
    student_cat = cat_lookup["Student"]
    profile_type = next(t for t in student_cat["types"] if t["name"] == "Student Profile")
    resume_text = """Durga Prasad
Email: durga.prasad@example.com
Phone: +91 98765 43210
Degree: Bachelor of Technology in Computer Science
CGPA: 8.7
Skills: Python, FastAPI, LangChain, Qdrant, React.js, PostgreSQL
"""
    res = requests.post(
        f"{BASE_URL}/api/documents/upload",
        files={"file": ("Student_Resume.txt", io.BytesIO(resume_text.encode("utf-8")), "text/plain")},
        data={"category_id": student_cat["id"], "type_id": profile_type["id"]},
    )
    assert res.status_code == 200
    doc_resume = res.json()
    print(f"✅ Uploaded Student Doc: '{doc_resume['filename']}' (ID={doc_resume['id']})")

    # Doc B: Study Material (Education > Study Materials)
    edu_cat = cat_lookup["Education"]
    study_type = next(t for t in edu_cat["types"] if t["name"] == "Study Materials")
    study_text = """Machine Learning Foundations
Machine learning is a method of data analysis that automates analytical model building based on the idea that systems can learn from data.
Supervised learning algorithms build a mathematical model of a set of data that contains both the inputs and the desired outputs.
Unsupervised learning algorithms take a set of data that contains only inputs, and find structure in the data, like grouping or clustering of data points.
"""
    res = requests.post(
        f"{BASE_URL}/api/documents/upload",
        files={"file": ("ML_Study_Notes.txt", io.BytesIO(study_text.encode("utf-8")), "text/plain")},
        data={"category_id": edu_cat["id"], "type_id": study_type["id"]},
    )
    assert res.status_code == 200
    doc_study = res.json()
    print(f"✅ Uploaded Education Doc: '{doc_study['filename']}' (ID={doc_study['id']})")

    # Doc C: Company Policy (Company > Company Policies)
    comp_cat = cat_lookup["Company"]
    policy_type = next(t for t in comp_cat["types"] if t["name"] == "Company Policies")
    policy_text = """Acme Innovations Corporate Policies
Annual Leave: All full-time employees receive 25 days of paid annual leave per calendar year.
Working Hours: Flexible core hours between 10:00 AM and 4:00 PM.
Travel Reimbursement: Domestic travel mileage is reimbursed at $0.65 per mile.
"""
    res = requests.post(
        f"{BASE_URL}/api/documents/upload",
        files={"file": ("Leave_Policy_2026.txt", io.BytesIO(policy_text.encode("utf-8")), "text/plain")},
        data={"category_id": comp_cat["id"], "type_id": policy_type["id"]},
    )
    assert res.status_code == 200
    doc_policy = res.json()
    print(f"✅ Uploaded Company Policy: '{doc_policy['filename']}' (ID={doc_policy['id']})")

    # Doc D: Healthcare Clinical Trial (Healthcare > Clinical Trials)
    trial_text = """Trial Protocol TX-904
Principal Investigator: Dr. Sarah Jenkins
Founding Year: 2023
Trial Phase: Phase 3 Multicenter Study
Target Disease: Type 2 Diabetes Mellitus
Primary Endpoint: Reduction in HbA1c levels after 24 weeks of oral administration.
"""
    res = requests.post(
        f"{BASE_URL}/api/documents/upload",
        files={"file": ("Trial_TX904.txt", io.BytesIO(trial_text.encode("utf-8")), "text/plain")},
        data={"category_id": health_cat["id"], "type_id": trial_type["id"]},
    )
    assert res.status_code == 200
    doc_trial = res.json()
    print(f"✅ Uploaded Healthcare Doc: '{doc_trial['filename']}' (ID={doc_trial['id']})")

    time.sleep(1)

    # ── 3. Document-Locked Sessions & Strict RAG QA ──────────
    print("\n3. Testing Document-Locked Chat Sessions...")

    # Session 1: Locked to Student_Resume.txt
    res = requests.post(f"{BASE_URL}/api/chat/sessions", json={"document_id": doc_resume["id"]})
    assert res.status_code == 201
    s_resume = res.json()
    s_resume_id = s_resume["id"]
    print(f"✅ Created locked session for Student Resume (ID={s_resume_id})")

    # Q1: Candidate name
    res = requests.post(f"{BASE_URL}/api/chat", json={"session_id": s_resume_id, "question": "What is the candidate's name?"})
    assert res.status_code == 200
    ans = res.json()["answer"]
    print(f"   Q: What is the candidate's name? -> A: '{ans}'")
    assert "Durga Prasad" in ans

    # Q2: Skills
    res = requests.post(f"{BASE_URL}/api/chat", json={"session_id": s_resume_id, "question": "What are the skills?"})
    assert res.status_code == 200
    ans = res.json()["answer"]
    print(f"   Q: What are the skills? -> A: '{ans}'")
    assert "FastAPI" in ans and "LangChain" in ans

    # Q3: Question from another document (Annual Leave) on Resume session -> MUST BE NOT FOUND
    res = requests.post(f"{BASE_URL}/api/chat", json={"session_id": s_resume_id, "question": "What is the annual leave allowance?"})
    assert res.status_code == 200
    ans = res.json()["answer"]
    print(f"   Q: What is the annual leave allowance? (on Resume session) -> A: '{ans}'")
    assert "information not found in the selected document" in ans.lower()

    # Session 2: Locked to Leave_Policy_2026.txt
    res = requests.post(f"{BASE_URL}/api/chat/sessions", json={"document_id": doc_policy["id"]})
    assert res.status_code == 201
    s_policy_id = res.json()["id"]

    # Q4: Annual leave on Policy session
    res = requests.post(f"{BASE_URL}/api/chat", json={"session_id": s_policy_id, "question": "What is the annual leave allowance?"})
    assert res.status_code == 200
    ans = res.json()["answer"]
    print(f"   Q: What is the annual leave allowance? (on Policy session) -> A: '{ans}'")
    assert "25 days" in ans.lower()

    # Q5: Resume question on Policy session -> MUST BE NOT FOUND
    res = requests.post(f"{BASE_URL}/api/chat", json={"session_id": s_policy_id, "question": "What is the candidate's name?"})
    assert res.status_code == 200
    ans = res.json()["answer"]
    print(f"   Q: What is the candidate's name? (on Policy session) -> A: '{ans}'")
    assert "information not found in the selected document" in ans.lower()

    # Session 3: Locked to Trial_TX904.txt
    res = requests.post(f"{BASE_URL}/api/chat/sessions", json={"document_id": doc_trial["id"]})
    assert res.status_code == 201
    s_trial_id = res.json()["id"]

    # Q6: Principal Investigator
    res = requests.post(f"{BASE_URL}/api/chat", json={"session_id": s_trial_id, "question": "Who is the Principal Investigator?"})
    assert res.status_code == 200
    ans = res.json()["answer"]
    print(f"   Q: Who is the Principal Investigator? -> A: '{ans}'")
    assert "Sarah Jenkins" in ans

    # ── 4. Verify Session History & Citations ────────────────
    print("\n4. Verifying Session History & Source Citations...")
    res = requests.get(f"{BASE_URL}/api/chat/sessions/{s_resume_id}")
    assert res.status_code == 200
    session_detail = res.json()
    assert len(session_detail["messages"]) >= 2
    print(f"✅ Session '{s_resume_id}' recorded {len(session_detail['messages'])} messages in PostgreSQL history")

    print("\n==================================================")
    print("🎉 ALL TEST SCENARIOS PASSED WITH 100% SUCCESS!")
    print("==================================================")

if __name__ == "__main__":
    run_suite()
