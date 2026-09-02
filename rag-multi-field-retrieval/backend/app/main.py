"""
RAG Document Assistant — FastAPI entry point with Category & Hierarchy support.
"""
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import engine, SessionLocal
from app.models import Base, Category, DocumentType
from app.rag.vectorstore import init_collection

load_dotenv()


def apply_db_migrations() -> None:
    """Apply incremental schema updates for existing database tables."""
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text("""
            ALTER TABLE IF EXISTS documents ADD COLUMN IF NOT EXISTS category_id INTEGER;
            ALTER TABLE IF EXISTS documents ADD COLUMN IF NOT EXISTS type_id INTEGER;
            ALTER TABLE IF EXISTS documents ADD COLUMN IF NOT EXISTS file_path VARCHAR(500);
            ALTER TABLE IF EXISTS chat_messages ADD COLUMN IF NOT EXISTS session_id VARCHAR(64);
            ALTER TABLE IF EXISTS chat_messages ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'assistant';
            
            -- Backfill legacy documents without category/type to Education / Study Materials
            UPDATE documents 
            SET category_id = (SELECT id FROM categories WHERE name = 'Education' LIMIT 1),
                type_id = (SELECT id FROM document_types WHERE name = 'Study Materials' LIMIT 1)
            WHERE category_id IS NULL;
        """))


def seed_default_categories(db: Session) -> None:
    """Seed comprehensive initial 16 categories and document types."""
    default_taxonomy = {
        "Company": [
            ("HR & Employee Details", "Employee records, rosters, and personnel details"),
            ("Company Policies", "HR guidelines, handbook, leave policies, and code of conduct"),
            ("Projects", "Company project descriptions, roadmaps, and reports"),
            ("Internal Documents", "Internal wikis, SOPs, and operating procedures"),
            ("Deployment & Technical Documents", "Deployment guides, architectures, and DevOps docs"),
            ("Benefits & Compensation", "Employee perks, healthcare, salary structures, and insurance"),
            ("Finance & Accounting", "Company financial statements, balance sheets, and budgets"),
            ("Departments", "Departmental overviews and organizational structures"),
            ("Operations", "Daily operations, facilities, and vendor management"),
            ("Compliance & Legal", "Legal compliance, audits, security protocols, and certifications"),
            ("Recruitment", "Job postings, screening criteria, and interview rubrics"),
            ("Training & Development", "Onboarding guides, skill training, and workshop materials"),
            ("Performance & Assessments", "Performance appraisals, KPI reviews, and evaluations"),
            ("Company Reports", "Quarterly and annual company performance reports"),
            ("Company Data / Excel Sheets", "Company spreadsheets, rosters, and numerical data"),
            ("Other", "Miscellaneous company documents"),
        ],
        "Education": [
            ("Study Materials", "Textbooks, revision guides, and lecture slides"),
            ("Research Papers", "Academic papers and conference publications"),
            ("Courses", "Course outlines, prerequisites, and learning objectives"),
            ("Subjects", "Syllabus, topic breakdowns, and subject guides"),
            ("Lecture Notes", "Classroom and lecture notes"),
            ("Assignments", "Homework, problem sets, and solutions"),
            ("Examinations", "Past papers, exam guidelines, and mock tests"),
            ("Assessments", "Tests, quizzes, evaluations, and grading rubrics"),
            ("Syllabus", "Official academic syllabus and curriculum guidelines"),
            ("Textbooks", "Prescribed textbooks and academic literature"),
            ("Academic Reports", "Institutional and academic research reports"),
            ("Learning Resources", "Supplementary reading and tutorial materials"),
            ("Training Materials", "Skill development and lab manuals"),
            ("Other", "Miscellaneous education documents"),
        ],
        "Business": [
            ("Business Plans", "Executive summaries, pitch decks, and roadmaps"),
            ("Business Reports", "Annual, quarterly, and operational business reports"),
            ("Business Strategy", "Corporate strategy, OKRs, and growth plans"),
            ("Financial Documents", "Financial statements, audit reports, and balance sheets"),
            ("Sales Documents", "Sales pitches, pipelines, and revenue projections"),
            ("Customer Documents", "Customer accounts, CRM data, and case studies"),
            ("Operations", "Supply chain, workflows, and process docs"),
            ("Business Analytics", "KPI dashboards and metric analysis"),
            ("Market Analysis", "Industry research and competitor analysis"),
            ("Contracts", "Business agreements and vendor contracts"),
            ("Business Proposals", "Client proposals, bids, and RFP responses"),
            ("Meeting Documents", "Meeting agendas, minutes, and action items"),
            ("Business Data / Excel", "Business spreadsheets, financial models, and tables"),
            ("Other", "Miscellaneous business documents"),
        ],
        "Marketing": [
            ("Marketing Strategy", "Go-to-market strategies and positioning briefs"),
            ("Campaigns", "Ad copy, campaign briefs, and marketing schedules"),
            ("Market Research", "Consumer surveys and market trend studies"),
            ("Customer Research", "Customer personas, feedback, and demographic data"),
            ("Advertising", "Ad creatives, budget allocations, and PPC specs"),
            ("Social Media Marketing", "Social content calendars, copies, and engagement plans"),
            ("Content Marketing", "Articles, blog posts, whitepapers, and guides"),
            ("SEO", "Keyword research, SEO audit reports, and rankings"),
            ("Email Marketing", "Email sequences, newsletters, and conversion copy"),
            ("Marketing Analytics", "Web traffic, conversion tracking, and user funnels"),
            ("Campaign Reports", "Campaign ROI and performance analysis"),
            ("Brand Documents", "Brand voice, identity, and style guides"),
            ("Competitor Analysis", "Competitive intelligence and positioning analysis"),
            ("Other", "Miscellaneous marketing documents"),
        ],
        "Projects": [
            ("Project Documentation", "Comprehensive project overviews and wikis"),
            ("Project Requirements", "Product Requirement Documents (PRD) and user stories"),
            ("Project Plans", "Project timeline, milestones, and resource allocation"),
            ("Project Reports", "Status reports, post-mortems, and retrospectives"),
            ("Technical Documentation", "Technical specifications and engineering designs"),
            ("Architecture Documents", "System architecture diagrams and flowcharts"),
            ("Deployment Documents", "Release manifests and deployment procedures"),
            ("API Documentation", "REST/GraphQL API specs and endpoint guides"),
            ("Project Data", "Project telemetry, test datasets, and tables"),
            ("Project Meetings", "Sprint standup notes, planning, and minutes"),
            ("Project Status Reports", "Weekly and monthly project status updates"),
            ("Other", "Miscellaneous project documents"),
        ],
        "Research": [
            ("Research Papers", "Academic papers and journal submissions"),
            ("Research Reports", "Investigative reports and whitepapers"),
            ("Literature Reviews", "Comprehensive surveys of related research"),
            ("Research Notes", "Lab notes, hypotheses, and research journals"),
            ("Datasets", "Data collection methodologies and data dictionaries"),
            ("Experiments", "Methodology, lab protocols, and experimental results"),
            ("Research Findings", "Conclusions, charts, and outcome summaries"),
            ("Case Studies", "In-depth case studies and field observations"),
            ("Technical Research", "Applied research and experimental architectures"),
            ("Academic Research", "University and scholarly research papers"),
            ("Other", "Miscellaneous research documents"),
        ],
        "Study": [
            ("Study Materials", "Comprehensive study materials and guides"),
            ("Study Notes", "Revision and topic study notes"),
            ("Lecture Notes", "Classroom and lecture notes"),
            ("Subject Notes", "Subject-wise reference notes"),
            ("Exam Preparation", "Past questions, tips, and mock tests"),
            ("Assignments", "Practice homework and exercises"),
            ("Practice Materials", "Worksheets and sample problem sets"),
            ("Question Papers", "Previous year and model question papers"),
            ("Other", "Other study documents"),
        ],
        "Students": [
            ("Student Profile", "Personal resumes, CVs, and student portfolios"),
            ("Personal Details", "Contact info, emergency contacts, and identification"),
            ("Education Details", "Degrees, transcripts, diplomas, and school history"),
            ("Marks / Grades", "Transcripts, grade reports, and scorecards"),
            ("Attendance", "Attendance records, registers, and absence logs"),
            ("Assignments", "Student submitted homework and assignments"),
            ("Projects", "Academic projects and capstone reports"),
            ("Certificates", "Certifications, awards, honors, and licenses"),
            ("Achievements", "Competitions, extracurriculars, and recognitions"),
            ("Student Resume", "Formatted resumes and curriculum vitae"),
            ("Assessments", "Student test results and evaluations"),
            ("Study Materials", "Personal study notes and exam preparation"),
            ("Other", "Miscellaneous student documents"),
        ],
        "Courses": [
            ("Python", "Python programming tutorials, notes, and code samples"),
            ("C", "C language manuals, syntax, and exercises"),
            ("C++", "C++ object-oriented concepts and examples"),
            ("Java", "Java core, enterprise, and frameworks"),
            ("JavaScript", "JavaScript ES6+, frontend, and Node.js"),
            ("SQL", "Database queries, schemas, and relational theory"),
            ("Data Science", "Data analysis, pandas, and visualization"),
            ("Machine Learning", "ML algorithms, models, and workflows"),
            ("Deep Learning", "Neural networks, PyTorch, and TensorFlow"),
            ("Artificial Intelligence", "AI search, NLP, and computer vision"),
            ("Web Development", "HTML, CSS, React, and web architecture"),
            ("Cloud Computing", "AWS, GCP, Azure, and cloud design"),
            ("DevOps", "CI/CD, Docker, Kubernetes, and automation"),
            ("Cybersecurity", "Network security, ethical hacking, and encryption"),
            ("Other", "Other course materials"),
        ],
        "Subjects": [
            ("Mathematics", "Calculus, linear algebra, and discrete math"),
            ("Physics", "Mechanics, electromagnetism, and optics"),
            ("Chemistry", "Organic, inorganic, and physical chemistry"),
            ("Computer Science", "Core computer science fundamentals"),
            ("Data Structures", "Arrays, trees, graphs, and linked lists"),
            ("Algorithms", "Sorting, search, dynamic programming, and complexity"),
            ("Database Management", "RDBMS, normalization, and ACID properties"),
            ("Operating Systems", "Process scheduling, memory, and file systems"),
            ("Computer Networks", "OSI model, TCP/IP, and routing protocols"),
            ("Artificial Intelligence", "Search algorithms, expert systems, and agents"),
            ("Machine Learning", "Supervised, unsupervised, and reinforcement learning"),
            ("Statistics", "Probability, distributions, and hypothesis testing"),
            ("Economics", "Microeconomics, macroeconomics, and market models"),
            ("Other", "Other academic subjects"),
        ],
        "Notes": [
            ("Study Notes", "Comprehensive study notes and exam revision"),
            ("Lecture Notes", "Classroom lecture transcripts and slides"),
            ("Technical Notes", "Cheat sheets, syntax guides, and architectures"),
            ("Meeting Notes", "Meeting agendas, decisions, and action items"),
            ("Project Notes", "Sprint ideas, bug logs, and discussions"),
            ("Research Notes", "Hypotheses, literature excerpts, and ideas"),
            ("Personal Notes", "Personal summaries and thoughts"),
            ("Course Notes", "Course-specific notes and walkthroughs"),
            ("Subject Notes", "Topic-by-topic subject explanations"),
            ("Other", "Other note documents"),
        ],
        "Assessments": [
            ("Exams", "Final exams, midterms, and answer keys"),
            ("Tests", "Class tests, unit tests, and quizzes"),
            ("Assignments", "Graded assignments and rubrics"),
            ("Quizzes", "Multiple choice questionnaires and flashcards"),
            ("Interview Assessments", "Technical and behavioral interview question sets"),
            ("Technical Assessments", "Coding challenges and system design tests"),
            ("Academic Assessments", "Standardized tests and academic evaluations"),
            ("Employee Assessments", "Employee skill assessments and reviews"),
            ("Performance Assessments", "Quarterly appraisals and 360-degree feedback"),
            ("Other", "Other assessment documents"),
        ],
        "Resume / CV": [
            ("Student Resume", "Fresh graduate and student resumes"),
            ("Professional Resume", "Experienced professional resumes"),
            ("Developer Resume", "Software engineer and developer CVs"),
            ("Technical Resume", "System architects and engineering profiles"),
            ("Academic CV", "Faculty and researcher curriculum vitae"),
            ("Executive Resume", "Leadership and managerial resumes"),
            ("Portfolio", "Design and project portfolios"),
            ("Career Profile", "Career summaries and bios"),
            ("Other", "Other resumes and profiles"),
        ],
        "News": [
            ("Technology News", "Tech industry developments and announcements"),
            ("Business News", "Corporate mergers, markets, and economic news"),
            ("Education News", "University rankings and educational reforms"),
            ("Financial News", "Stock market, banking, and crypto news"),
            ("Marketing News", "Brand campaigns and digital media updates"),
            ("AI News", "Artificial intelligence breakthroughs and LLM updates"),
            ("Science News", "Scientific discoveries and space exploration"),
            ("Industry News", "Domain-specific industry bulletins"),
            ("Company News", "Internal and press announcements"),
            ("Other", "Other news articles and feeds"),
        ],
        "Articles": [
            ("Technical Articles", "In-depth engineering tutorials and articles"),
            ("Business Articles", "Thought leadership and business essays"),
            ("Educational Articles", "Pedagogy and learning methodologies"),
            ("Research Articles", "Summaries of scientific discoveries"),
            ("Marketing Articles", "Growth hacking and branding case studies"),
            ("Technology Articles", "Emerging technology reviews"),
            ("Industry Articles", "Trade publication articles"),
            ("Opinion Articles", "Editorials and commentary pieces"),
            ("Blog Articles", "Web posts and longform blog articles"),
            ("Other", "Other articles"),
        ],
        "Social Media": [
            ("LinkedIn", "LinkedIn posts, articles, and profile content"),
            ("Instagram", "Instagram captions, carousel copy, and reels scripts"),
            ("Facebook", "Facebook group posts and page updates"),
            ("X / Twitter", "Tweets, threads, and short updates"),
            ("YouTube", "Video descriptions, scripts, and transcripts"),
            ("Social Media Posts", "Cross-platform social media copy"),
            ("Social Media Campaigns", "Hashtag campaigns and social strategies"),
            ("Social Media Analytics", "Engagement metrics, impressions, and followers"),
            ("Social Media Reports", "Monthly social performance reports"),
            ("Other", "Other social media content"),
        ],
        "Other": [
            ("Custom Type", "User-defined custom document type"),
            ("General Documents", "General letters, notices, and memos"),
            ("Miscellaneous", "Unclassified files and documents"),
            ("Other", "Other document types"),
        ],
    }

    try:
        existing_cats = {c.name.lower(): c for c in db.query(Category).all()}
        # Normalize student -> students
        if "student" in existing_cats and "students" not in existing_cats:
            existing_cats["student"].name = "Students"
            db.commit()
            existing_cats = {c.name.lower(): c for c in db.query(Category).all()}

        for cat_name, types in default_taxonomy.items():
            cat = existing_cats.get(cat_name.lower())
            if not cat:
                cat = Category(name=cat_name, description=f"{cat_name} documents and records")
                db.add(cat)
                db.flush()
                existing_cats[cat_name.lower()] = cat

            existing_types = {t.name.lower(): t for t in cat.types}
            for type_name, type_desc in types:
                if type_name.lower() not in existing_types:
                    dt = DocumentType(
                        category_id=cat.id,
                        name=type_name,
                        description=type_desc,
                    )
                    db.add(dt)
        db.commit()
        print("✅ Default taxonomy (16 categories) initialized.")
    except Exception as e:
        db.rollback()
        print(f"⚠️ Error seeding categories: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle events."""
    # ── Startup ──────────────────────────────────────────────
    # 1. Create tables & apply incremental migrations
    Base.metadata.create_all(bind=engine)
    apply_db_migrations()
    
    # 2. Seed default taxonomy
    db = SessionLocal()
    try:
        seed_default_categories(db)
    finally:
        db.close()

    # Ensure the Qdrant collection exists
    init_collection()
    
    # Create uploads directory
    os.makedirs("uploads", exist_ok=True)
    yield
    # ── Shutdown ─────────────────────────────────────────────


app = FastAPI(
    title="Universal Document-Based RAG Assistant",
    description="Multi-Category, Multi-Type, Document-Specific RAG Assistant",
    version="2.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────
from app.api.categories import router as categories_router  # noqa: E402
from app.api.documents import router as documents_router   # noqa: E402
from app.api.chat import router as chat_router             # noqa: E402

app.include_router(categories_router, prefix="/api")
app.include_router(documents_router, prefix="/api")
app.include_router(chat_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "message": "Universal Document-Based RAG Assistant API is running",
        "version": "2.0.0",
    }
