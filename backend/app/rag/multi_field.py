"""
Multi-field query decomposition, field-level retrieval, extraction, and coverage validation.
Ensures that when a user asks for multiple fields in a single query, EVERY requested field is
identified, independently retrieved, accurately extracted, and verified before returning.
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel
from langchain_core.documents import Document

from app.rag.deduplicator import deduplicate_documents, deduplicate_sentences, normalize_text
from app.rag.cleaner import clean_extracted_text

NOT_AVAILABLE_MSG = "Not available in the selected document."


class FieldDefinition(BaseModel):
    key: str
    display_name: str
    synonyms: List[str]
    sub_query: str
    retrieval_keywords: List[str]
    section_headers: List[str]


# Standard field catalog
FIELD_CATALOG: List[FieldDefinition] = [
    FieldDefinition(
        key="name",
        display_name="Name",
        synonyms=["name", "full name", "candidate name", "employee name", "person name", "who is this"],
        sub_query="What is the full name of the candidate or person or employee?",
        retrieval_keywords=["name", "candidate", "employee", "profile", "author"],
        section_headers=["name", "personal information", "profile", "candidate"],
    ),
    FieldDefinition(
        key="email",
        display_name="Email",
        synonyms=["email", "email id", "mail id", "email address", "mail address", "mail", "e-mail"],
        sub_query="What is the email address or mail ID?",
        retrieval_keywords=["email", "mail", "@", "gmail", "outlook", "contact"],
        section_headers=["contact", "personal information", "profile", "contact details"],
    ),
    FieldDefinition(
        key="phone",
        display_name="Phone",
        synonyms=["phone", "phone number", "mobile", "mobile number", "contact number", "telephone", "cell", "cell number"],
        sub_query="What is the phone number or mobile contact number?",
        retrieval_keywords=["phone", "mobile", "tel", "contact", "+91", "+1"],
        section_headers=["contact", "personal information", "profile", "contact details"],
    ),
    FieldDefinition(
        key="linkedin",
        display_name="LinkedIn",
        synonyms=["linkedin", "linkedin id", "linkedin url", "linkedin profile", "linkedin link"],
        sub_query="What is the LinkedIn profile URL or link?",
        retrieval_keywords=["linkedin", "linkedin.com", "in/"],
        section_headers=["contact", "links", "social", "profiles", "personal information"],
    ),
    FieldDefinition(
        key="github",
        display_name="GitHub",
        synonyms=["github", "github id", "github url", "github profile", "github link", "git hub"],
        sub_query="What is the GitHub profile URL or link?",
        retrieval_keywords=["github", "github.com", "repositories", "git"],
        section_headers=["contact", "links", "social", "profiles", "personal information"],
    ),
    FieldDefinition(
        key="portfolio",
        display_name="Portfolio / Website",
        synonyms=["portfolio", "website", "personal website", "portfolio link", "portfolio url", "blog"],
        sub_query="What is the portfolio URL or personal website?",
        retrieval_keywords=["portfolio", "website", "http", "https", "blog"],
        section_headers=["contact", "links", "profiles"],
    ),
    FieldDefinition(
        key="professional_summary",
        display_name="Professional Summary",
        synonyms=["professional summary", "summary", "profile summary", "about me", "about", "career objective", "executive summary", "overview", "objective"],
        sub_query="What is the professional summary, profile summary, career objective, or about section?",
        retrieval_keywords=["summary", "profile", "about", "objective", "overview", "background"],
        section_headers=["professional summary", "summary", "profile summary", "about me", "objective", "career objective", "executive summary"],
    ),
    FieldDefinition(
        key="skills",
        display_name="Skills",
        synonyms=["skills", "skill set", "all skills", "skill", "core competencies", "competencies", "abilities"],
        sub_query="What are the skills, core competencies, and abilities listed?",
        retrieval_keywords=["skills", "skill", "competencies", "abilities", "proficiencies"],
        section_headers=["skills", "technical skills", "core competencies", "key skills", "skills & abilities", "skills set"],
    ),
    FieldDefinition(
        key="technical_skills",
        display_name="Technical Skills / Technologies",
        synonyms=["technical skills", "technologies", "tech stack", "technology", "programming languages", "tools & technologies", "technical competencies", "frameworks", "tools"],
        sub_query="What technical skills, programming languages, frameworks, databases, and technologies are listed?",
        retrieval_keywords=["technical skills", "technologies", "programming languages", "frameworks", "databases", "tools", "tech stack"],
        section_headers=["technical skills", "technologies", "programming languages", "tools & technologies", "tech stack", "skills"],
    ),
    FieldDefinition(
        key="education",
        display_name="Education",
        synonyms=["education", "education details", "educational background", "academic details", "academics", "qualifications", "degree", "university", "college", "schooling", "gpa", "cgpa"],
        sub_query="What education details, degrees, universities, colleges, CGPA, and graduation years are listed?",
        retrieval_keywords=["education", "degree", "university", "college", "bachelor", "master", "b.tech", "m.tech", "cgpa", "gpa", "academic"],
        section_headers=["education", "educational background", "academics", "qualifications", "academic background"],
    ),
    FieldDefinition(
        key="projects",
        display_name="Projects",
        synonyms=["projects", "project section", "project details", "key projects", "academic projects", "personal projects", "past projects"],
        sub_query="What projects, project descriptions, technologies used, and key accomplishments are listed?",
        retrieval_keywords=["projects", "project", "developed", "built", "implemented", "architecture", "system"],
        section_headers=["projects", "key projects", "academic projects", "personal projects", "project experience"],
    ),
    FieldDefinition(
        key="experience",
        display_name="Work Experience",
        synonyms=["experience", "work experience", "employment history", "work history", "employment", "internships", "internship", "professional experience"],
        sub_query="What work experience, employment history, companies, roles, and job responsibilities are listed?",
        retrieval_keywords=["experience", "employment", "work experience", "company", "role", "software engineer", "intern", "developer"],
        section_headers=["experience", "work experience", "employment history", "professional experience", "work history"],
    ),
    FieldDefinition(
        key="certifications",
        display_name="Certifications",
        synonyms=["certifications", "certificates", "licenses", "courses", "certified"],
        sub_query="What certifications, certificates, and accredited courses are listed?",
        retrieval_keywords=["certifications", "certificate", "certified", "license", "course"],
        section_headers=["certifications", "certificates", "licenses", "courses & certifications"],
    ),
    FieldDefinition(
        key="benefits",
        display_name="Employee Benefits",
        synonyms=["employee benefits", "benefits", "perks", "allowances", "compensation benefits"],
        sub_query="What employee benefits, perks, and compensation allowances are provided?",
        retrieval_keywords=["benefits", "perks", "health insurance", "allowance", "vacation", "retirement"],
        section_headers=["employee benefits", "benefits", "perks", "compensation & benefits"],
    ),
    FieldDefinition(
        key="policy",
        display_name="Policy Details",
        synonyms=["leave policy", "vacation policy", "policy", "policies", "rules", "regulations", "guidelines"],
        sub_query="What is the leave policy, workplace policy, rules, and guidelines?",
        retrieval_keywords=["policy", "leave", "annual leave", "sick leave", "rules", "guidelines", "regulations"],
        section_headers=["policy", "leave policy", "company policy", "rules & regulations"],
    ),
    FieldDefinition(
        key="languages",
        display_name="Languages",
        synonyms=["languages known", "spoken languages", "languages", "language proficiencies"],
        sub_query="What languages are spoken or known?",
        retrieval_keywords=["languages", "english", "hindi", "spanish", "fluent"],
        section_headers=["languages", "languages known", "spoken languages"],
    ),
]


def decompose_query(question: str) -> List[FieldDefinition]:
    """
    Analyze a user question and identify all requested distinct information fields.
    Preserves exact user intent and order of fields.
    """
    q_lower = question.lower()
    
    # Normalize punctuation and separators in question for matching
    norm_q = re.sub(r"[,;+&|/\\?!\n]+", " ", q_lower)
    norm_q = re.sub(r"\s+", " ", norm_q).strip()

    detected_fields: List[FieldDefinition] = []
    seen_keys = set()

    # Match against synonyms in order of specificity (longer synonym phrases first)
    sorted_catalog = sorted(
        FIELD_CATALOG,
        key=lambda f: max(len(s) for s in f.synonyms),
        reverse=True
    )

    for field in sorted_catalog:
        if field.key in seen_keys:
            continue

        # Check if any synonym matches
        matched = False
        for syn in field.synonyms:
            # Word-boundary matching for synonym
            pattern = r"\b" + re.escape(syn) + r"\b"
            if re.search(pattern, norm_q):
                matched = True
                break

        if matched:
            # Distinguish general 'skills' vs 'technical skills'
            # If both are requested, keep both. If only 'technical skills' is requested, don't duplicate 'skills' unless explicit
            detected_fields.append(field)
            seen_keys.add(field.key)

    # Sort detected fields by their appearance position in the original question
    def get_pos(f: FieldDefinition) -> int:
        positions = [norm_q.find(syn) for syn in f.synonyms if norm_q.find(syn) != -1]
        return min(positions) if positions else 999

    detected_fields.sort(key=get_pos)
    return detected_fields


def is_multi_field_query(question: str) -> bool:
    """Return True if user question requests 2 or more distinct fields."""
    fields = decompose_query(question)
    return len(fields) >= 2


def extract_field_from_text(field: FieldDefinition, context: str, local_extractor=None) -> str:
    """
    Extract high-precision answer for a specific field from the provided context.
    Returns the exact extracted value, or 'Not available in the selected document.'
    """
    if not context or not context.strip():
        return NOT_AVAILABLE_MSG

    text = context.strip()
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # 1. Exact regex extractors for structured fields
    if field.key == "email":
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        if email_match:
            return email_match.group(0).strip()
        return NOT_AVAILABLE_MSG

    if field.key == "phone":
        for line in lines:
            if any(k in line.lower() for k in ["phone", "mobile", "tel", "contact"]):
                m = re.search(r"(?:phone|mobile|tel|contact(?:\s+number)?)\s*[:=-]\s*([^\s|;,]+(?:\s+[^\s|;,]+)*)", line, re.I)
                if m:
                    val = m.group(1).strip()
                    if any(c.isdigit() for c in val):
                        return val
        phone_match = re.search(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,5}\)?[-.\s]?\d{3,5}[-.\s]?\d{3,5}", text)
        if phone_match and len(re.sub(r"\D", "", phone_match.group(0))) >= 7:
            return phone_match.group(0).strip()
        return NOT_AVAILABLE_MSG

    if field.key == "linkedin":
        link_match = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\.-]+", text, re.I)
        if link_match:
            return link_match.group(0).strip()
        for line in lines:
            if "linkedin" in line.lower():
                m = re.search(r"linkedin\s*[:=-]\s*([^\s,;]+)", line, re.I)
                if m:
                    return m.group(1).strip()
        return NOT_AVAILABLE_MSG

    if field.key == "github":
        git_match = re.search(r"(?:https?://)?(?:www\.)?github\.com/[\w\.-]+", text, re.I)
        if git_match:
            return git_match.group(0).strip()
        for line in lines:
            if "github" in line.lower():
                m = re.search(r"github\s*[:=-]\s*([^\s,;]+)", line, re.I)
                if m:
                    return m.group(1).strip()
        return NOT_AVAILABLE_MSG

    if field.key == "portfolio":
        for line in lines:
            if any(k in line.lower() for k in ["portfolio", "website"]):
                m = re.search(r"(?:portfolio|website)\s*[:=-]\s*([^\s,;]+)", line, re.I)
                if m:
                    return m.group(1).strip()
        return NOT_AVAILABLE_MSG

    if field.key == "name":
        for line in lines:
            m = re.search(r"^(?:candidate\s+name|student\s+name|author\s+name|employee\s+name|employee|candidate|student|full\s+name|name)\s*[:=-]\s*(.+)$", line, re.I)
            if m:
                return m.group(1).strip()
        if lines and not lines[0].startswith("#") and ":" not in lines[0]:
            first_line = lines[0].strip()
            first_words = first_line.split()
            disallowed = ["policy", "manual", "guide", "handbook", "protocol", "report", "company", "notes", "document", "resume", "cv"]
            if not any(dw in first_line.lower() for dw in disallowed) and 2 <= len(first_words) <= 3 and all(w[0].isupper() for w in first_words if w.isalpha()):
                return first_line
        return NOT_AVAILABLE_MSG

    # 2. Direct section extraction for structured multi-line sections
    from app.rag.chain import _parse_sections, _extract_items_from_body
    sections = _parse_sections(lines)

    if field.key in ["skills", "technical_skills"]:
        for sec in sections:
            h_low = sec["header"].lower()
            if any(k in h_low for k in ["skill", "technolog", "tech stack", "programming", "tools", "competenc"]):
                items = _extract_items_from_body(sec["body"], sec["header"])
                if items:
                    return "\n".join(f"- {it}" for it in items)
                elif sec["body"]:
                    return "\n".join(f"- {l.lstrip('-*• ')}" for l in sec["body"])

    if field.key == "education":
        for sec in sections:
            h_low = sec["header"].lower()
            if any(k in h_low for k in ["education", "academic", "qualification", "degree"]):
                items = _extract_items_from_body(sec["body"], sec["header"])
                if items:
                    return "\n".join(f"- {it}" for it in items)
                elif sec["body"]:
                    return "\n".join(f"- {l.lstrip('-*• ')}" for l in sec["body"])

    if field.key == "projects":
        for sec in sections:
            h_low = sec["header"].lower()
            if any(k in h_low for k in ["project"]):
                items = _extract_items_from_body(sec["body"], sec["header"])
                if items:
                    return "\n".join(f"- {it}" for it in items)
                elif sec["body"]:
                    return "\n".join(f"- {l.lstrip('-*• ')}" for l in sec["body"])

    if field.key == "professional_summary":
        for sec in sections:
            h_low = sec["header"].lower()
            if any(k in h_low for k in ["summary", "about", "objective", "overview"]):
                if sec["body"]:
                    return " ".join(sec["body"]).strip()

    if field.key == "experience":
        for sec in sections:
            h_low = sec["header"].lower()
            if any(k in h_low for k in ["experience", "employment", "work history", "internship"]):
                items = _extract_items_from_body(sec["body"], sec["header"])
                if items:
                    return "\n".join(f"- {it}" for it in items)
                elif sec["body"]:
                    return "\n".join(f"- {l.lstrip('-*• ')}" for l in sec["body"])

    if field.key == "certifications":
        for sec in sections:
            h_low = sec["header"].lower()
            if any(k in h_low for k in ["certification", "certificate", "license", "course"]):
                items = _extract_items_from_body(sec["body"], sec["header"])
                if items:
                    return "\n".join(f"- {it}" for it in items)
                elif sec["body"]:
                    return "\n".join(f"- {l.lstrip('-*• ')}" for l in sec["body"])

    # 3. Fallback extraction using LocalGroundedChatModel or query matching
    if local_extractor is not None:
        extracted = local_extractor._extract_exact_answer(field.sub_query, text)
        if extracted and not any(p in extracted.lower() for p in ["not found in the", "not available in the", "this answer is not available", "this information is not available"]):
            return extracted

    return NOT_AVAILABLE_MSG


def format_multi_field_response(field_results: List[Tuple[FieldDefinition, str]]) -> str:
    """
    Format the multi-field results into a clean, markdown-structured response.
    Never drops any requested field.
    """
    sections = []
    for field, answer in field_results:
        clean_ans = answer.strip() if answer else NOT_AVAILABLE_MSG
        sections.append(f"### {field.display_name}\n{clean_ans}")

    return "\n\n".join(sections)
