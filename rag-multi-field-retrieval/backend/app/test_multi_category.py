"""
Automated verification for Multi-Category, Multi-Type, Document-Specific RAG Chatbot.
"""
import requests
import io
import time

BASE_URL = "http://localhost:8000"

def test_multi_category_rag():
    print("=== 🚀 Starting Multi-Category RAG Verification ===")

    # 1. Fetch Categories
    res = requests.get(f"{BASE_URL}/api/categories")
    assert res.status_code == 200
    categories = res.json()
    assert len(categories) >= 10
    print(f"✅ Loaded {len(categories)} categories")

    cat_map = {c["name"]: c for c in categories}
    
    # Check Education category and Study Materials type
    edu_cat = cat_map["Education"]
    study_type = next((t for t in edu_cat["types"] if t["name"] == "Study Materials"), None)
    assert study_type is not None, "Study Materials type missing in Education"

    # Check Company category and Policies type
    comp_cat = cat_map["Company"]
    policy_type = next((t for t in comp_cat["types"] if t["name"] == "Company Policies"), None)
    assert policy_type is not None, "Company Policies type missing in Company"

    # 2. Upload Document 1: Machine Learning.txt (under Education > Study Materials)
    ml_content = """Machine Learning Notes
Supervised learning uses labeled training data to learn mapping functions from input variables to an output variable.
Unsupervised learning models the underlying structure or distribution in data in order to learn more about the data.
Reinforcement learning trains an agent to make a sequence of decisions by rewarding positive behaviors and punishing negative ones.
"""
    ml_file = {"file": ("Machine Learning.txt", io.BytesIO(ml_content.encode("utf-8")), "text/plain")}
    res = requests.post(
        f"{BASE_URL}/api/documents/upload",
        files=ml_file,
        data={"category_id": edu_cat["id"], "type_id": study_type["id"]},
    )
    assert res.status_code == 200, f"Upload ML failed: {res.text}"
    ml_doc = res.json()
    assert ml_doc["category_name"] == "Education"
    assert ml_doc["type_name"] == "Study Materials"
    print(f"✅ Uploaded '{ml_doc['filename']}' (ID={ml_doc['id']}) under Education > Study Materials")

    # 3. Upload Document 2: Deep Learning.txt (under Education > Study Materials)
    dl_content = """Deep Learning Architectures
Convolutional Neural Networks (CNNs) are specialized for processing grid-structured topology such as image data.
Recurrent Neural Networks (RNNs) and LSTMs process sequential data like natural language and time series.
Transformers utilize self-attention mechanisms to parallelize training on large sequence datasets.
"""
    dl_file = {"file": ("Deep Learning.txt", io.BytesIO(dl_content.encode("utf-8")), "text/plain")}
    res = requests.post(
        f"{BASE_URL}/api/documents/upload",
        files=dl_file,
        data={"category_id": edu_cat["id"], "type_id": study_type["id"]},
    )
    assert res.status_code == 200, f"Upload DL failed: {res.text}"
    dl_doc = res.json()
    print(f"✅ Uploaded '{dl_doc['filename']}' (ID={dl_doc['id']}) under Education > Study Materials")

    # 4. Upload Document 3: Company_Policy.txt (under Company > Company Policies)
    policy_content = """Acme Corp Company Policy
Leave Policy: Employees are entitled to 24 days of paid annual leave per calendar year.
Working Hours: Standard core hours are 9:00 AM to 5:00 PM Monday through Friday.
Remote Work: Employees can work remotely up to 3 days per week upon manager approval.
"""
    policy_file = {"file": ("Company_Policy.txt", io.BytesIO(policy_content.encode("utf-8")), "text/plain")}
    res = requests.post(
        f"{BASE_URL}/api/documents/upload",
        files=policy_file,
        data={"category_id": comp_cat["id"], "type_id": policy_type["id"]},
    )
    assert res.status_code == 200, f"Upload Policy failed: {res.text}"
    policy_doc = res.json()
    print(f"✅ Uploaded '{policy_doc['filename']}' (ID={policy_doc['id']}) under Company > Company Policies")

    time.sleep(1)

    # 5. Create Document-Locked Chat Session for Machine Learning.pdf
    res = requests.post(f"{BASE_URL}/api/chat/sessions", json={"document_id": ml_doc["id"]})
    assert res.status_code == 201, f"Session create failed: {res.text}"
    ml_session = res.json()
    ml_session_id = ml_session["id"]
    print(f"✅ Created locked Chat Session (ID={ml_session_id}) for '{ml_doc['filename']}'")

    # 6. Test Multi-Turn Chat locked to Machine Learning.pdf
    print("\n--- 🔍 Testing Document-Specific Chat (Session Locked to Machine Learning.pdf) ---")
    
    # Q1: "What is supervised learning?"
    res = requests.post(f"{BASE_URL}/api/chat", json={"session_id": ml_session_id, "question": "What is supervised learning?"})
    assert res.status_code == 200
    ans1 = res.json()["answer"]
    print(f"✅ Q1: What is supervised learning?\n   A: {ans1}")
    assert "labeled training data" in ans1.lower()

    # Q2: Question about Deep Learning on Machine Learning doc session (must return NOT found)
    res = requests.post(f"{BASE_URL}/api/chat", json={"session_id": ml_session_id, "question": "What are Convolutional Neural Networks?"})
    assert res.status_code == 200
    ans2 = res.json()["answer"]
    print(f"✅ Q2: What are Convolutional Neural Networks? (on ML doc session)\n   A: {ans2}")
    assert "not available in the selected document" in ans2.lower()

    # Q3: Question about Company Policy on Machine Learning doc session (must return NOT found)
    res = requests.post(f"{BASE_URL}/api/chat", json={"session_id": ml_session_id, "question": "What is the leave policy?"})
    assert res.status_code == 200
    ans3 = res.json()["answer"]
    print(f"✅ Q3: What is the leave policy? (on ML doc session)\n   A: {ans3}")
    assert "not available in the selected document" in ans3.lower()

    # 7. Test "Change Document" to Company_Policy.docx
    print("\n--- 🔄 Testing Switch / Change Document to Company_Policy.docx ---")
    res = requests.post(f"{BASE_URL}/api/chat/sessions", json={"document_id": policy_doc["id"]})
    assert res.status_code == 201
    policy_session = res.json()
    policy_session_id = policy_session["id"]
    print(f"✅ Switched to locked Chat Session (ID={policy_session_id}) for '{policy_doc['filename']}'")

    # Q4: Ask leave policy on Company_Policy session
    res = requests.post(f"{BASE_URL}/api/chat", json={"session_id": policy_session_id, "question": "What is the leave policy?"})
    assert res.status_code == 200
    ans4 = res.json()["answer"]
    print(f"✅ Q4: What is the leave policy? (on Company Policy session)\n   A: {ans4}")
    assert "24 days" in ans4.lower()

    # Q5: Ask machine learning question on Company Policy session (must return NOT found)
    res = requests.post(f"{BASE_URL}/api/chat", json={"session_id": policy_session_id, "question": "What is supervised learning?"})
    assert res.status_code == 200
    ans5 = res.json()["answer"]
    print(f"✅ Q5: What is supervised learning? (on Company Policy session)\n   A: {ans5}")
    assert "not available in the selected document" in ans5.lower()

    print("\n🎉 ALL MULTI-CATEGORY & DOCUMENT ISOLATION TESTS PASSED WITH 100% SUCCESS!")

if __name__ == "__main__":
    test_multi_category_rag()
