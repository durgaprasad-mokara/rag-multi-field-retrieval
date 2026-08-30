"""
Comprehensive test suite verifying the master fix for RAG output and answer extraction.
Verifies that:
1. Section headings (e.g. TECHNICAL SKILLS, EMPLOYEE BENEFITS) are NEVER returned as answers.
2. The actual content/items/list/definitions under sections are extracted correctly.
3. Universal across resume, company doc, education doc, research doc, technical doc, and tables.
4. Missing info returns fallback message.
"""
from app.rag.chain import LocalGroundedChatModel, FALLBACK_MSG

def test_rag_output_fix():
    extractor = LocalGroundedChatModel()

    print("==================================================================")
    print("🚀 TESTING RAG OUTPUT / ANSWER EXTRACTION FIX")
    print("==================================================================")

    # ── Test 1: Resume Technical Skills ─────────────────────────────────
    resume_context = """
Durga Prasad
Email: durga@example.com | Phone: +1 555-0199 | CGPA: 8.9 / 10

TECHNICAL SKILLS
Programming: Python, Java, C++, SQL
Frontend: React, JavaScript, HTML, CSS
Backend: FastAPI, Node.js
Database: PostgreSQL, MongoDB
AI: LangChain, LangGraph

EXPERIENCE
Software Engineer at TechCorp (2023 - Present)
- Developed RAG pipelines using LangChain and Qdrant.
- Built responsive user interfaces in React.
"""
    ans1 = extractor._extract_exact_answer("skills set", resume_context)
    print("\n1. Resume - 'skills set':\n", ans1)
    assert ans1 != "TECHNICAL SKILLS", "FAILED: Returned section heading 'TECHNICAL SKILLS'!"
    assert "Python" in ans1 and "FastAPI" in ans1 and "PostgreSQL" in ans1, f"FAILED: Skills missing! Got: {ans1}"

    ans1_name = extractor._extract_exact_answer("What is the name?", resume_context)
    print("\n   Resume - 'What is the name?':", ans1_name)
    assert ans1_name == "Durga Prasad"

    ans1_phone = extractor._extract_exact_answer("What is the phone number?", resume_context)
    print("   Resume - 'What is the phone number?':", ans1_phone)
    assert "+1 555-0199" in ans1_phone

    ans1_missing = extractor._extract_exact_answer("What is the driver license number?", resume_context)
    print("   Resume - Missing info query:", ans1_missing)
    assert "information not found" in ans1_missing.lower() or "not available" in ans1_missing.lower()

    # ── Test 2: Company Employee Benefits ───────────────────────────────
    company_context = """
EMPLOYEE BENEFITS
Health Insurance
Paid Leave
Retirement Benefits
Performance Bonus

LEAVE POLICY
All full-time employees receive 25 days of paid annual leave per calendar year.
"""
    ans2 = extractor._extract_exact_answer("What are the employee benefits?", company_context)
    print("\n2. Company Doc - 'What are the employee benefits?':\n", ans2)
    assert ans2 != "EMPLOYEE BENEFITS", "FAILED: Returned section heading 'EMPLOYEE BENEFITS'!"
    assert "Health Insurance" in ans2 and "Paid Leave" in ans2 and "Performance Bonus" in ans2

    ans2_leave = extractor._extract_exact_answer("What is the leave policy?", company_context)
    print("\n   Company Doc - 'What is the leave policy?':\n", ans2_leave)
    assert ans2_leave != "LEAVE POLICY", "FAILED: Returned section heading 'LEAVE POLICY'!"
    assert "25 days" in ans2_leave

    # ── Test 3: Research Paper Objectives ───────────────────────────────
    research_context = """
RESEARCH OBJECTIVES
The study aims to evaluate the therapeutic efficacy and safety profile of TX-904 in adult patients.

PRINCIPAL INVESTIGATOR
Dr. Sarah Jenkins
"""
    ans3 = extractor._extract_exact_answer("What are the research objectives?", research_context)
    print("\n3. Research Paper - 'What are the research objectives?':\n", ans3)
    assert ans3 != "RESEARCH OBJECTIVES", "FAILED: Returned section heading 'RESEARCH OBJECTIVES'!"
    assert "evaluate the therapeutic efficacy" in ans3

    ans3_pi = extractor._extract_exact_answer("Who is the Principal Investigator?", research_context)
    print("   Research Paper - 'Who is the Principal Investigator?':", ans3_pi)
    assert "Dr. Sarah Jenkins" in ans3_pi

    # ── Test 4: Education Document Course Objectives ────────────────────
    edu_context = """
COURSE OBJECTIVES
Students will learn Python programming, data structures, algorithms, and problem solving.

PREREQUISITES
Basic understanding of algebra and logical reasoning.
"""
    ans4 = extractor._extract_exact_answer("What are the course objectives?", edu_context)
    print("\n4. Education Doc - 'What are the course objectives?':\n", ans4)
    assert ans4 != "COURSE OBJECTIVES", "FAILED: Returned section heading 'COURSE OBJECTIVES'!"
    assert "Python programming" in ans4 and "data structures" in ans4

    # ── Test 5: Technical / Python Document ─────────────────────────────
    python_context = """
WHAT IS PYTHON?
Python is a high-level, interpreted programming language known for its clear syntax and dynamic typing.
"""
    ans5 = extractor._extract_exact_answer("What is Python?", python_context)
    print("\n5. Python Doc - 'What is Python?':\n", ans5)
    assert ans5 != "WHAT IS PYTHON?", "FAILED: Returned heading 'WHAT IS PYTHON?'!"
    assert "high-level, interpreted programming language" in ans5

    # ── Test 6: Table Support ───────────────────────────────────────────
    table_context = """
TECHNICAL MATRIX
| Skill | Level |
| Python | Advanced |
| SQL | Intermediate |
"""
    ans6_col = extractor._extract_exact_answer("What skills are listed?", table_context)
    print("\n6. Table - 'What skills are listed?':\n", ans6_col)
    assert "Python" in ans6_col and "SQL" in ans6_col

    ans6_cell = extractor._extract_exact_answer("What is the Python skill level?", table_context)
    print("   Table - 'What is the Python skill level?':", ans6_cell)
    assert "Advanced" in ans6_cell

    print("\n==================================================================")
    print("🎉 ALL RAG ANSWER EXTRACTION TESTS PASSED PERFECTLY!")
    print("==================================================================")

if __name__ == "__main__":
    test_rag_output_fix()
