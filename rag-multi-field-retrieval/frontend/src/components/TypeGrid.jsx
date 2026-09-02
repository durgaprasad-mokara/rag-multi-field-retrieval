import React, { useState } from "react";
import {
  Layers,
  ChevronRight,
  ArrowLeft,
  Plus,
  FileText,
  FolderPlus,
} from "lucide-react";
import { getCategoryIcon } from "./CategoryGrid";
import { createDocumentType } from "../services/api";

export default function TypeGrid({
  category,
  onSelectType,
  onBackToCategories,
  onCategoriesUpdated,
  onError,
}) {
  const [isAddingType, setIsAddingType] = useState(false);
  const [newTypeName, setNewTypeName] = useState("");
  const [newTypeDesc, setNewTypeDesc] = useState("");

  const types = category.types || [];

  async function handleAddType(e) {
    e.preventDefault();
    if (!newTypeName.trim()) return;
    try {
      await createDocumentType(category.id, {
        name: newTypeName.trim(),
        description: newTypeDesc.trim() || null,
      });
      setNewTypeName("");
      setNewTypeDesc("");
      setIsAddingType(false);
      onCategoriesUpdated();
    } catch (err) {
      onError(err.response?.data?.detail || "Failed to add document type");
    }
  }

  return (
    <div className="type-grid-container">
      {/* Header with Navigation & Category Title */}
      <div className="grid-header">
        <div className="type-header-content">
          <button
            className="btn btn-secondary btn-sm btn-back"
            onClick={onBackToCategories}
          >
            <ArrowLeft size={14} /> Back to Categories
          </button>

          <div className="type-title-row">
            <div className="type-category-icon">
              {getCategoryIcon(category.name, 28)}
            </div>
            <div>
              <h2 className="grid-main-title">{category.name} Document Types</h2>
              <p className="grid-main-subtitle">
                Select a subcategory to upload documents and launch a scoped RAG session
              </p>
            </div>
          </div>
        </div>

        <button
          className="btn btn-primary btn-sm"
          onClick={() => setIsAddingType(true)}
        >
          <Plus size={15} /> Add Document Type
        </button>
      </div>

      {/* Add Type Form Modal / Inline */}
      {isAddingType && (
        <form onSubmit={handleAddType} className="form-card type-add-card">
          <h4>Add New Document Type under {category.name}</h4>
          <div className="form-row" style={{ marginTop: "8px" }}>
            <input
              type="text"
              placeholder="Type Name (e.g. Employees, Syllabus, Notes)"
              value={newTypeName}
              onChange={(e) => setNewTypeName(e.target.value)}
              className="input-text"
              autoFocus
              required
            />
            <input
              type="text"
              placeholder="Optional Description"
              value={newTypeDesc}
              onChange={(e) => setNewTypeDesc(e.target.value)}
              className="input-text"
            />
          </div>
          <div
            style={{
              display: "flex",
              gap: "8px",
              justifyContent: "flex-end",
              marginTop: "10px",
            }}
          >
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setIsAddingType(false)}
            >
              Cancel
            </button>
            <button type="submit" className="btn btn-primary btn-sm">
              Save Type
            </button>
          </div>
        </form>
      )}

      {/* Types Grid */}
      <div className="type-cards-grid">
        {types.length > 0 ? (
          types.map((type) => {
            const docCount = type.document_count || 0;

            return (
              <div
                key={type.id}
                className="type-card"
                onClick={() => onSelectType(type)}
              >
                <div className="type-card-top">
                  <div className="type-icon-bubble">
                    <Layers size={20} />
                  </div>
                  <span className="badge-doc-count">
                    {docCount} Doc{docCount !== 1 ? "s" : ""}
                  </span>
                </div>

                <h3 className="type-card-name">{type.name}</h3>
                <p className="type-card-desc">
                  {type.description || `Documents belonging to ${category.name} > ${type.name}.`}
                </p>

                <div className="type-card-footer">
                  <span className="type-footer-cta">View Documents &amp; Upload</span>
                  <ChevronRight size={16} className="type-arrow" />
                </div>
              </div>
            );
          })
        ) : (
          <div className="type-empty-state">
            <Layers size={36} className="empty-icon" />
            <h3>No Document Types in {category.name} yet</h3>
            <p>Click "Add Document Type" above to create the first subcategory.</p>
          </div>
        )}
      </div>
    </div>
  );
}
