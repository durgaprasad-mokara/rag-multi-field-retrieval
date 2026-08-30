"""
Automated Test for the Hierarchical Category -> Type -> Document -> Scoped Chat Flow.
"""
import requests
import io
import time
from app.database import SessionLocal
from app.main import seed_default_categories

BASE_URL = "http://localhost:8000"

def run_test():
    print("==================================================================")
    print("🚀 TESTING HIERARCHICAL WORKFLOW: CATEGORY -> TYPE -> DOC -> CHAT")
    print("==================================================================")

    # 0. Ensure Database has all seeded taxonomy categories and types
    db = SessionLocal()
    try:
        seed_default_categories(db)
    finally:
        db.close()

    # 1. Step 1: Fetch Main Categories
    print("\nStep 1: Listing Main Categories (Landing Screen)...")
    res = requests.get(f"{BASE_URL}/api/categories")
    assert res.status_code == 200
    categories = res.json()
    cat_names = [c["name"] for c in categories]
    print(f"✅ Retrieved {len(categories)} categories: {', '.join(cat_names)}")
    
    required_cats = ["Company", "Education", "Students", "Business", "Marketing", "Projects", "Research", "Courses", "Notes", "Assessments", "Resume / CV", "News", "Articles", "Social Media", "Other"]
    for req in required_cats:
        assert req in cat_names, f"Missing required category: {req}"

    # 2. Step 2: Select 'Company' Category & View Types
    print("\nStep 2: Selecting 'Company' and fetching Category-Specific Types...")
    company_cat = next(c for c in categories if c["name"] == "Company")
    res = requests.get(f"{BASE_URL}/api/categories/{company_cat['id']}/types")
    assert res.status_code == 200
    company_types = res.json()
    type_names = [t["name"] for t in company_types]
    print(f"✅ Company Document Types ({len(company_types)}): {', '.join(type_names)}")
    assert "Employees" in type_names
    assert "Company Policies" in type_names
    assert "Benefits" in type_names

    # 3. Step 3: Select 'Employees' Type and Upload Scoped Documents
    print("\nStep 3: Selecting 'Company -> Employees' and uploading scoped documents...")
    employees_type = next(t for t in company_types if t["name"] == "Employees")
    
    # Upload Employee 001
    emp1_text = """Employee Profile: John Smith
Employee ID: EMP-101
Designation: Senior Software Engineer
Department: Core Infrastructure
Email: john.smith@company.com
Phone: +1 555-0199
Skills: Python, FastAPI, Kubernetes, PostgreSQL
"""
    res = requests.post(
        f"{BASE_URL}/api/documents/upload",
        files={"file": ("Employee_001.txt", io.BytesIO(emp1_text.encode("utf-8")), "text/plain")},
        data={"category_id": company_cat["id"], "type_id": employees_type["id"]},
    )
    assert res.status_code == 200
    doc_emp1 = res.json()
    print(f"✅ Uploaded to Company -> Employees: {doc_emp1['filename']} (ID={doc_emp1['id']})")

    # Upload Employee 002
    emp2_text = """Employee Profile: Alice Wang
Employee ID: EMP-102
Designation: Product Designer
Department: UX & Design
Email: alice.wang@company.com
Phone: +1 555-0244
Skills: Figma, Design Systems, User Research, Prototyping
"""
    res = requests.post(
        f"{BASE_URL}/api/documents/upload",
        files={"file": ("Employee_002.txt", io.BytesIO(emp2_text.encode("utf-8")), "text/plain")},
        data={"category_id": company_cat["id"], "type_id": employees_type["id"]},
    )
    assert res.status_code == 200
    doc_emp2 = res.json()
    print(f"✅ Uploaded to Company -> Employees: {doc_emp2['filename']} (ID={doc_emp2['id']})")

    # 4. Step 4: Document-Locked Chat with Single Document (Employee_001.txt)
    print("\nStep 4: Starting Document-Locked Chat with Employee_001.txt...")
    res = requests.post(f"{BASE_URL}/api/chat/sessions", json={"document_id": doc_emp1["id"]})
    assert res.status_code == 201
    session1 = res.json()
    session1_id = session1["id"]
    print(f"✅ Created locked session: {session1_id} for {doc_emp1['filename']}")

    # Q1: Employee Name
    res = requests.post(f"{BASE_URL}/api/chat", json={"session_id": session1_id, "question": "What is the employee's name?"})
    assert res.status_code == 200
    ans1 = res.json()["answer"]
    print(f"   Q: What is the employee's name? -> A: '{ans1}'")
    assert "John Smith" in ans1

    # Q2: Employee Phone
    res = requests.post(f"{BASE_URL}/api/chat", json={"session_id": session1_id, "question": "What is the employee's phone number?"})
    assert res.status_code == 200
    ans2 = res.json()["answer"]
    print(f"   Q: What is the employee's phone number? -> A: '{ans2}'")
    assert "+1 555-0199" in ans2

    # Q3: Question about Alice Wang (Employee 002) on Employee 001 session -> MUST FAIL WITH FALLBACK
    res = requests.post(f"{BASE_URL}/api/chat", json={"session_id": session1_id, "question": "What is Alice Wang's designation?"})
    assert res.status_code == 200
    ans3 = res.json()["answer"]
    print(f"   Q: What is Alice Wang's designation? (on EMP 001 session) -> A: '{ans3}'")
    assert "information not found in the selected document" in ans3.lower()

    # 5. Step 5: Multi-Document Scoped Chat (Employee_001.txt + Employee_002.txt)
    print("\nStep 5: Testing Multi-Document Selection Mode...")
    res = requests.post(
        f"{BASE_URL}/api/chat",
        json={
            "document_ids": [doc_emp1["id"], doc_emp2["id"]],
            "question": "What are the skills of both employees?",
        },
    )
    assert res.status_code == 200
    multi_ans = res.json()["answer"]
    print(f"   Q: What are the skills of both employees? -> A: '{multi_ans}'")
    assert "Python" in multi_ans or "Figma" in multi_ans

    print("\n==================================================================")
    print("🎉 ALL HIERARCHICAL WORKFLOW TESTS PASSED PERFECTLY!")
    print("==================================================================")

if __name__ == "__main__":
    run_test()
