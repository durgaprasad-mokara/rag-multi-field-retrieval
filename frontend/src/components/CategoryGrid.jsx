import React from "react";
import {
  Building2,
  GraduationCap,
  Briefcase,
  Megaphone,
  FolderKanban,
  Microscope,
  UserCheck,
  BookOpen,
  FileText,
  BarChart3,
  Layers,
  Plus,
  ChevronRight,
  Folder,
} from "lucide-react";

// Category icon mapper helper
export function getCategoryIcon(name, size = 24) {
  const n = name.toLowerCase();
  if (n.includes("company")) return <Building2 size={size} />;
  if (n.includes("education")) return <GraduationCap size={size} />;
  if (n.includes("business")) return <Briefcase size={size} />;
  if (n.includes("marketing")) return <Megaphone size={size} />;
  if (n.includes("project")) return <FolderKanban size={size} />;
  if (n.includes("research")) return <Microscope size={size} />;
  if (n.includes("student")) return <UserCheck size={size} />;
  if (n.includes("course")) return <BookOpen size={size} />;
  if (n.includes("note")) return <FileText size={size} />;
  if (n.includes("assessment")) return <BarChart3 size={size} />;
  return <Folder size={size} />;
}

export default function CategoryGrid({
  categories,
  onSelectCategory,
  onOpenCategoryManager,
}) {
  return (
    <div className="category-grid-container">
      <div className="grid-header">
        <div>
          <h2 className="grid-main-title">Select a Document Category</h2>
          <p className="grid-main-subtitle">
            Choose a knowledge domain to explore document types and start a document-locked AI chat
          </p>
        </div>
        <button
          className="btn btn-secondary btn-sm"
          onClick={onOpenCategoryManager}
          title="Manage Categories and Types"
        >
          <Layers size={15} /> Manage Categories
        </button>
      </div>

      <div className="category-cards-grid">
        {categories.map((cat) => {
          const typeCount = cat.types?.length || 0;
          const docCount = cat.document_count || 0;

          return (
            <div
              key={cat.id}
              className="category-card"
              onClick={() => onSelectCategory(cat)}
            >
              <div className="category-card-top">
                <div className="category-icon-bubble">
                  {getCategoryIcon(cat.name, 26)}
                </div>
                <div className="category-badges">
                  <span className="badge-type-count">{typeCount} Types</span>
                  {docCount > 0 && (
                    <span className="badge-doc-count">
                      {docCount} Doc{docCount !== 1 ? "s" : ""}
                    </span>
                  )}
                </div>
              </div>

              <h3 className="category-card-name">{cat.name}</h3>
              <p className="category-card-desc">
                {cat.description || `${cat.name} documents, records, and files.`}
              </p>

              <div className="category-card-footer">
                <span className="category-footer-hint">
                  {cat.types && cat.types.length > 0
                    ? cat.types.slice(0, 3).map((t) => t.name).join(", ") +
                      (cat.types.length > 3 ? "..." : "")
                    : "No subcategories yet"}
                </span>
                <ChevronRight size={18} className="category-arrow" />
              </div>
            </div>
          );
        })}

        {/* Add New Category Quick Card */}
        <div
          className="category-card add-category-card"
          onClick={onOpenCategoryManager}
        >
          <div className="add-category-icon">
            <Plus size={32} />
          </div>
          <h3>Add Custom Category</h3>
          <p>Create a new domain or industry taxonomy for your documents</p>
        </div>
      </div>
    </div>
  );
}
