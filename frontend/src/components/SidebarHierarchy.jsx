/**
 * SidebarHierarchy — Left sidebar.
 *
 * STRICT RULES:
 * 1. Renders ONLY: Category headers → Type names.
 * 2. NEVER renders uploaded filenames or document arrays.
 * 3. Clicking a category expands its accordion.
 * 4. Clicking a type SELECTS it (no immediate file picker).
 * 5. Browse Files / drag-drop validates category+type before uploading.
 * 6. After upload the sidebar does NOT change — no filenames appear.
 */
import React, { useState, useRef } from "react";
import {
  Building2,
  GraduationCap,
  Briefcase,
  Megaphone,
  FolderKanban,
  Microscope,
  BookOpen,
  UserCheck,
  BarChart3,
  BookMarked,
  FileText,
  FileBadge,
  Newspaper,
  ScrollText,
  Share2,
  Package,
  ChevronRight,
  ChevronDown,
  Upload,
  MessageSquare,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import { uploadDocument } from "../services/api";

/** Colored icon for each category name */
export function getCategoryIcon(name, size = 15) {
  const n = name.toLowerCase();
  if (n.includes("company"))    return <Building2    size={size} className="cat-icon cat-company"     />;
  if (n.includes("education"))  return <GraduationCap size={size} className="cat-icon cat-education"  />;
  if (n.includes("business"))   return <Briefcase    size={size} className="cat-icon cat-business"    />;
  if (n.includes("marketing"))  return <Megaphone    size={size} className="cat-icon cat-marketing"   />;
  if (n.includes("project"))    return <FolderKanban size={size} className="cat-icon cat-projects"    />;
  if (n.includes("research"))   return <Microscope   size={size} className="cat-icon cat-research"    />;
  if (n.includes("study"))      return <BookOpen     size={size} className="cat-icon cat-study"       />;
  if (n.includes("student"))    return <UserCheck    size={size} className="cat-icon cat-students"    />;
  if (n.includes("assessment")) return <BarChart3    size={size} className="cat-icon cat-assessments" />;
  if (n.includes("course"))     return <BookOpen     size={size} className="cat-icon cat-courses"     />;
  if (n.includes("subject"))    return <BookMarked   size={size} className="cat-icon cat-subjects"    />;
  if (n.includes("note"))       return <FileText     size={size} className="cat-icon cat-notes"       />;
  if (n.includes("resume") || n.includes("cv")) return <FileBadge size={size} className="cat-icon cat-resume" />;
  if (n.includes("news"))       return <Newspaper    size={size} className="cat-icon cat-news"        />;
  if (n.includes("article"))    return <ScrollText   size={size} className="cat-icon cat-articles"    />;
  if (n.includes("social"))     return <Share2       size={size} className="cat-icon cat-social"      />;
  return                               <Package      size={size} className="cat-icon cat-other"       />;
}

export default function SidebarHierarchy({
  categories,
  activeCategory,
  activeType,
  onSelectCategory,
  onSelectType,
  onDocumentUploaded,
  onError,
}) {
  // Which category accordions are open (navigation state only)
  const [openCats, setOpenCats] = useState(() => {
    const init = {};
    if (categories?.[0]) init[categories[0].id] = true;
    return init;
  });

  const [uploading, setUploading] = useState(false);
  const [uploadDone, setUploadDone] = useState(false);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef(null);

  // ── Toggle category accordion ────────────────────────────────
  const toggleCat = (cat) => {
    const willOpen = !openCats[cat.id];
    setOpenCats((prev) => ({ ...prev, [cat.id]: !prev[cat.id] }));
    if (willOpen) onSelectCategory(cat);
  };

  // ── Select type (no file picker here) ───────────────────────
  const handleTypeClick = (cat, type) => {
    onSelectCategory(cat);
    onSelectType(type);
  };

  // ── Browse Files: validate then open OS picker ───────────────
  const handleBrowseClick = (e) => {
    e.stopPropagation();
    if (uploading) return;
    if (!activeCategory || !activeType) {
      onError("Please select a Category and a Type below before uploading.");
      return;
    }
    fileInputRef.current?.click();
  };

  // ── Drag-and-drop ─────────────────────────────────────────────
  const handleDragOver = (e) => { e.preventDefault(); setDragging(true); };
  const handleDragLeave = () => setDragging(false);
  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    if (!activeCategory || !activeType) {
      onError("Please select a Category and a Type before dropping a file.");
      return;
    }
    handleFiles(e.dataTransfer.files);
  };

  // ── Upload handler ────────────────────────────────────────────
  // Uploads to backend bound to activeCategory + activeType.
  // The sidebar is NEVER modified — no filenames added here.
  async function handleFiles(files) {
    if (!files?.length) return;
    if (!activeCategory || !activeType) {
      onError("Select a Category and a Type before uploading.");
      return;
    }

    setUploading(true);
    setUploadDone(false);

    try {
      for (let i = 0; i < files.length; i++) {
        const newDoc = await uploadDocument(files[i], activeCategory.id, activeType.id);
        onDocumentUploaded(newDoc, activeCategory, activeType);
      }
      setUploadDone(true);
      setTimeout(() => setUploadDone(false), 3000);
    } catch (err) {
      onError(err.response?.data?.detail || "Upload failed. Please try again.");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  return (
    <aside className="sidebar-container">

      {/* ── Branding ─────────────────────────────────────────── */}
      <div className="sidebar-header-section">
        <div className="sidebar-brand-row">
          <MessageSquare size={17} className="brand-logo-icon" />
          <h1 className="sidebar-title">RAG Assistant</h1>
        </div>
        <p className="sidebar-subtitle">Upload documents &amp; chat with AI</p>
      </div>

      {/* ── Upload Zone ───────────────────────────────────────── */}
      <div className="sidebar-upload-wrapper">
        <div
          className={`dropzone-box${dragging ? " drag-active" : ""}${uploading ? " is-uploading" : ""}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          {/* Hidden native file input */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.doc,.txt,.md,.csv,.xlsx,.xls,.html,.htm,.json"
            style={{ display: "none" }}
            onChange={(e) => handleFiles(e.target.files)}
          />

          <div className="upload-tray-icon">
            {uploadDone
              ? <CheckCircle2 size={24} className="text-success" />
              : <Upload size={24} />
            }
          </div>

          {uploading ? (
            <p className="drop-main-text">Uploading…</p>
          ) : uploadDone ? (
            <p className="drop-main-text text-success">Uploaded! Ready to chat.</p>
          ) : (
            <>
              <p className="drop-main-text">Drag &amp; Drop files here</p>
              <span className="drop-or-text">or</span>
            </>
          )}

          <button
            type="button"
            className="btn-browse-pill"
            onClick={handleBrowseClick}
            disabled={uploading}
          >
            {uploading ? "Uploading…" : "Browse Files"}
          </button>

          {/* Contextual upload scope hint */}
          {activeCategory && activeType && !uploading && !uploadDone && (
            <p className="upload-scope-hint">
              → {activeCategory.name} › {activeType.name}
            </p>
          )}
          {!activeCategory && (
            <p className="upload-scope-hint upload-scope-warn">
              <AlertTriangle size={10} /> Select a category below first
            </p>
          )}
          {activeCategory && !activeType && (
            <p className="upload-scope-hint upload-scope-warn">
              <AlertTriangle size={10} /> Now select a type below
            </p>
          )}
        </div>
      </div>

      {/* ── CATEGORIES Label ─────────────────────────────────── */}
      <div className="categories-header-label">
        <span>CATEGORIES</span>
      </div>

      {/* ── Category → Type List ─────────────────────────────── */}
      {/* RULE: This section NEVER renders documents or filenames. */}
      <div className="categories-scroll-area">
        {categories.map((cat) => {
          const isOpen = !!openCats[cat.id];
          const types  = cat.types || [];

          return (
            <div key={cat.id} className="category-group">

              {/* Category header row */}
              <div
                className={`category-item-header${isOpen ? " is-open" : ""}`}
                onClick={() => toggleCat(cat)}
              >
                <div className="category-name-group">
                  <span className="category-icon-wrapper">
                    {getCategoryIcon(cat.name, 14)}
                  </span>
                  <span className="category-text-label">{cat.name}</span>
                </div>
                <span className="category-chevron-icon">
                  {isOpen ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                </span>
              </div>

              {/* Expanded type rows — bullet dots only, NO filenames */}
              {isOpen && (
                <div className="subcategory-types-list">
                  {types.map((type) => {
                    const isSelected =
                      activeType?.id === type.id && activeCategory?.id === cat.id;
                    return (
                      <div
                        key={type.id}
                        className={`type-item-row${isSelected ? " is-selected" : ""}`}
                        onClick={() => handleTypeClick(cat, type)}
                        title={type.name}
                      >
                        <span className="type-bullet-dot">•</span>
                        <span className="type-item-name">{type.name}</span>
                        {isSelected && <span className="type-selected-indicator">✓</span>}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

    </aside>
  );
}
