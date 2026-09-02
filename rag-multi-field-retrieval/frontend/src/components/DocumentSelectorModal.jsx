import React, { useState } from "react";
import {
  FileText,
  Folder,
  Layers,
  Check,
  X,
  Search,
  MessageSquare,
} from "lucide-react";

export default function DocumentSelectorModal({
  categories,
  documents,
  selectedDocId,
  onSelectDocument,
  onClose,
}) {
  const [selectedCatId, setSelectedCatId] = useState(
    categories[0]?.id || ""
  );
  const [selectedTypeId, setSelectedTypeId] = useState("");
  const [searchFilter, setSearchFilter] = useState("");

  const activeCategory = categories.find(
    (c) => c.id === Number(selectedCatId)
  );
  const availableTypes = activeCategory?.types || [];

  const handleCategoryChange = (catId) => {
    setSelectedCatId(catId);
    const cat = categories.find((c) => c.id === catId);
    if (cat?.types?.length > 0) {
      setSelectedTypeId(cat.types[0].id);
    } else {
      setSelectedTypeId("");
    }
  };

  // Filter documents
  let displayedDocs = documents;
  if (searchFilter.trim()) {
    displayedDocs = documents.filter((d) =>
      d.filename.toLowerCase().includes(searchFilter.toLowerCase())
    );
  } else {
    if (selectedCatId) {
      displayedDocs = displayedDocs.filter(
        (d) => d.category_id === Number(selectedCatId)
      );
    }
    if (selectedTypeId) {
      displayedDocs = displayedDocs.filter(
        (d) => d.type_id === Number(selectedTypeId)
      );
    }
  }

  return (
    <div className="modal-backdrop">
      <div className="modal-card modal-card-lg">
        <div className="modal-header">
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div className="modal-icon-badge">
              <FileText size={20} />
            </div>
            <div>
              <h3>Select Active Document</h3>
              <p className="modal-subtitle">
                Choose the exact document to lock this RAG chat session to
              </p>
            </div>
          </div>
          <button className="btn-icon" onClick={onClose} title="Close">
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          {/* Search bar */}
          <div className="modal-search-row">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              placeholder="Search across all documents..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="input-text"
            />
          </div>

          {!searchFilter && (
            <div className="selector-columns-grid">
              {/* Category selector */}
              <div className="selector-col">
                <label className="col-label">Category</label>
                <div className="col-list">
                  {categories.map((c) => (
                    <button
                      key={c.id}
                      className={`col-item-btn ${
                        Number(selectedCatId) === c.id ? "active" : ""
                      }`}
                      onClick={() => handleCategoryChange(c.id)}
                    >
                      <Folder size={14} />
                      <span className="col-item-text">{c.name}</span>
                      <span className="col-item-count">
                        {c.document_count || 0}
                      </span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Type selector */}
              <div className="selector-col">
                <label className="col-label">Document Type</label>
                <div className="col-list">
                  {availableTypes.length > 0 ? (
                    availableTypes.map((t) => (
                      <button
                        key={t.id}
                        className={`col-item-btn ${
                          Number(selectedTypeId) === t.id ? "active" : ""
                        }`}
                        onClick={() => setSelectedTypeId(t.id)}
                      >
                        <Layers size={13} />
                        <span className="col-item-text">{t.name}</span>
                        <span className="col-item-count">
                          {t.document_count || 0}
                        </span>
                      </button>
                    ))
                  ) : (
                    <p className="empty-sub-hint">No types available</p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Document list */}
          <div className="modal-doc-results-section">
            <label className="col-label">
              Available Documents ({displayedDocs.length})
            </label>
            <div className="modal-doc-grid">
              {displayedDocs.length > 0 ? (
                displayedDocs.map((doc) => {
                  const isSelected = selectedDocId === doc.id;
                  return (
                    <div
                      key={doc.id}
                      className={`modal-doc-card ${
                        isSelected ? "selected" : ""
                      }`}
                      onClick={() => {
                        onSelectDocument(doc);
                        onClose();
                      }}
                    >
                      <div className="doc-card-top">
                        <FileText size={18} className="doc-card-icon" />
                        <span className="doc-card-title">{doc.filename}</span>
                      </div>
                      <div className="doc-card-meta">
                        <span className="meta-tag">{doc.category_name}</span>
                        <span className="meta-tag">{doc.type_name}</span>
                        <span className="meta-size">
                          {(doc.file_size / 1024).toFixed(1)} KB
                        </span>
                      </div>
                      {isSelected && (
                        <div className="selected-badge">
                          <Check size={12} /> Currently Selected
                        </div>
                      )}
                    </div>
                  );
                })
              ) : (
                <div className="modal-empty-docs">
                  <p>No documents found matching the selection.</p>
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
