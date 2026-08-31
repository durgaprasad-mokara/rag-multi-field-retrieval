"""
Document chunker — splits documents into structure-aware, document-type-aware pieces for embedding.
Preserves sections, handles lists and tables, prevents heading-only orphan chunks, and enriches hierarchical metadata.
"""
import re
from typing import Optional, List
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


def _detect_heading(line: str) -> Optional[str]:
    """Identify if a line is likely a section heading."""
    clean = line.strip()
    if not clean:
        return None
    
    # Markdown header
    if re.match(r"^#{1,4}\s+(.+)$", clean):
        return re.sub(r"^#{1,4}\s+", "", clean).strip()
    
    # Capitalized / short section title with or without colon
    # e.g. "TECHNICAL SKILLS", "EMPLOYEE BENEFITS:", "EDUCATION", "Course Objectives"
    if len(clean) <= 60:
        if clean.endswith(":") and len(clean.split()) <= 6:
            return clean.rstrip(":").strip()
        # All caps line with 1-6 words
        words = clean.split()
        if 1 <= len(words) <= 6 and clean.isupper() and any(c.isalpha() for c in clean):
            return clean.strip()
            
    return None


def _get_document_strategy(category_name: Optional[str], type_name: Optional[str], filename: str) -> str:
    """Identify the optimal chunking strategy based on category, type, and filename."""
    meta_str = f"{category_name or ''} {type_name or ''} {filename}".lower()
    if any(k in meta_str for k in ["resume", "cv", "candidate", "curriculum vitae", "developer resume"]):
        return "resume"
    elif any(k in meta_str for k in ["policy", "compliance", "handbook", "hr details", "benefit", "leave"]):
        return "policy"
    elif any(k in meta_str for k in ["research", "paper", "journal", "clinical trial", "study notes", "academic"]):
        return "research"
    elif any(k in meta_str for k in ["course", "education", "lecture", "tutorial", "subject"]):
        return "study"
    elif any(k in meta_str for k in ["technical", "api", "code", "architecture", "deployment"]):
        return "technical"
    return "general"


def split_documents(
    documents: list[Document],
    document_id: int,
    filename: str,
    category_id: Optional[int] = None,
    category_name: Optional[str] = None,
    type_id: Optional[int] = None,
    type_name: Optional[str] = None,
    chunk_size: int = 768,
    chunk_overlap: int = 128,
) -> list[Document]:
    """
    Split a list of LangChain Documents into smaller chunks with rich hierarchical metadata
    and document-type-aware boundary awareness.
    """
    strategy = _get_document_strategy(category_name, type_name, filename)

    # Strategy-specific separators
    if strategy == "resume":
        separators = [
            "\n\n\n",
            "\n\n",
            "\nEXPERIENCE",
            "\nEDUCATION",
            "\nSKILLS",
            "\nPROJECTS",
            "\nCERTIFICATIONS",
            "\n",
            "; ",
            ". ",
            " ",
            "",
        ]
    elif strategy == "policy":
        separators = [
            "\n\n\n",
            "\n\n",
            "\nPURPOSE",
            "\nSCOPE",
            "\nPOLICY",
            "\nRULES",
            "\nRESPONSIBILITIES",
            "\nPROCEDURES",
            "\n",
            "; ",
            ". ",
            " ",
            "",
        ]
    elif strategy == "research":
        separators = [
            "\n\n\n",
            "\n\n",
            "\nABSTRACT",
            "\nINTRODUCTION",
            "\nMETHODOLOGY",
            "\nMETHODS",
            "\nRESULTS",
            "\nDISCUSSION",
            "\nCONCLUSION",
            "\nREFERENCES",
            "\n",
            "; ",
            ". ",
            " ",
            "",
        ]
    else:
        separators = ["\n\n\n", "\n\n", "\n", "; ", ". ", " ", ""]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=separators,
    )

    chunks = splitter.split_documents(documents)

    valid_chunks = []
    chunk_idx = 0
    current_section = None

    for chunk in chunks:
        content = chunk.page_content.strip()
        if not content or len(content) < 5:
            continue

        # Check if content starts with or contains a prominent section heading
        for line in content.splitlines()[:3]:
            h = _detect_heading(line)
            if h:
                current_section = h
                break

        chunk.page_content = content
        
        # Preserve page number from loader if present
        page_num = chunk.metadata.get("page")
        if page_num is not None:
            try:
                page_num = int(page_num) + 1  # 1-indexed
            except Exception:
                page_num = None

        chunk.metadata.update(
            {
                "document_id": document_id,
                "category_id": category_id,
                "category_name": category_name or "",
                "type_id": type_id,
                "type_name": type_name or "",
                "filename": filename,
                "document_name": filename,
                "section": current_section or "",
                "section_name": current_section or "",
                "page_number": page_num,
                "chunk_id": chunk_idx,
                "chunk_index": chunk_idx,
                "strategy": strategy,
                "source_reference": f"{filename} (p. {page_num})" if page_num else filename,
            }
        )
        valid_chunks.append(chunk)
        chunk_idx += 1

    return valid_chunks

