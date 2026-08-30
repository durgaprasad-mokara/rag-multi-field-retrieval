import React, { useState } from "react";
import {
  Folder,
  ChevronRight,
  ChevronDown,
  FileText,
  Trash2,
  CheckCircle2,
  Clock,
  AlertCircle,
  Search,
} from "lucide-react";

export default function DocumentTree({
  categories,
  documents,
  selectedDocId,
  onSelectDocument,
  onDeleteDocument,
}) {
  const [openCategories, setOpenCategories] = useState({});
  const [openTypes, setOpenTypes] = useState({});
  const [searchTerm, setSearchTerm] = useState("");

  const toggleCategory = (catId) => {
    setOpenCategories((prev) => ({ ...prev, [catId]: !prev[catId] }));
  };

  const toggleType = (typeId) => {
    setOpenTypes((prev) => ({ ...prev, [typeId]: !prev[typeId] }));
  };

  // Group documents by category_id and type_id
  const docsByCategoryAndType = {};
  documents.forEach((doc) => {
    if (!docsByCategoryAndType[doc.category_id]) {
      docsByCategoryAndType[doc.category_id] = {};
    }
    if (!docsByCategoryAndType[doc.category_id][doc.type_id]) {
      docsByCategoryAndType[doc.category_id][doc.type_id] = [];
    }
    docsByCategoryAndType[doc.category_id][doc.type_id].push(doc);
  });

  const filteredDocuments = documents.filter((doc) =>
    doc.filename.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="document-tree-container">
      <div className="tree-header">
        <span className="tree-title">Document Explorer</span>
        <span className="badge-count">{documents.length} Total</span>
      </div>

      {documents.length > 5 && (
        <div className="tree-search-box">
          <Search size={14} className="search-icon" />
          <input
            type="text"
            placeholder="Search documents..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>
      )}

      {/* ── Search Mode Active ───────────────────────────── */}
      {searchTerm ? (
        <div className="search-results-list">
          {filteredDocuments.length > 0 ? (
            filteredDocuments.map((doc) => (
              <div
                key={doc.id}
                className={`tree-doc-item ${
                  selectedDocId === doc.id ? "active" : ""
                }`}
                onClick={() => onSelectDocument(doc)}
              >
                <FileText size={15} className="doc-icon" />
                <div className="doc-info">
                  <span className="doc-name">{doc.filename}</span>
                  <span className="doc-meta">
                    {doc.category_name} &gt; {doc.type_name}
                  </span>
                </div>
                <button
                  className="btn-icon-xs text-danger"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteDocument(doc.id);
                  }}
                  title="Delete Document"
                >
                  <Trash2 size={12} />
                </button>
              </div>
            ))
          ) : (
            <p className="empty-hint">No matching documents found.</p>
          )}
        </div>
      ) : (
        /* ── Hierarchical Tree Mode ──────────────────────── */
        <div className="tree-hierarchy-list">
          {categories.map((cat) => {
            const catDocs = documents.filter((d) => d.category_id === cat.id);
            const isCatOpen = openCategories[cat.id] ?? (catDocs.length > 0);

            return (
              <div key={cat.id} className="tree-category-node">
                {/* Category Header */}
                <div
                  className="tree-node-row category-row"
                  onClick={() => toggleCategory(cat.id)}
                >
                  {isCatOpen ? (
                    <ChevronDown size={15} className="chevron-icon" />
                  ) : (
                    <ChevronRight size={15} className="chevron-icon" />
                  )}
                  <Folder size={15} className="folder-icon" />
                  <span className="node-name">{cat.name}</span>
                  {catDocs.length > 0 && (
                    <span className="badge-count-doc-sm">
                      {catDocs.length}
                    </span>
                  )}
                </div>

                {/* Types under Category */}
                {isCatOpen && (
                  <div className="tree-types-container">
                    {cat.types && cat.types.length > 0 ? (
                      cat.types.map((type) => {
                        const typeDocs =
                          docsByCategoryAndType[cat.id]?.[type.id] || [];
                        const isTypeOpen =
                          openTypes[type.id] ?? (typeDocs.length > 0);

                        return (
                          <div key={type.id} className="tree-type-node">
                            {/* Type Row */}
                            <div
                              className="tree-node-row type-row"
                              onClick={() => toggleType(type.id)}
                            >
                              {isTypeOpen ? (
                                <ChevronDown
                                  size={13}
                                  className="chevron-icon"
                                />
                              ) : (
                                <ChevronRight
                                  size={13}
                                  className="chevron-icon"
                                />
                              )}
                              <span className="type-node-bullet">•</span>
                              <span className="node-name type-name">
                                {type.name}
                              </span>
                              {typeDocs.length > 0 && (
                                <span className="badge-count-sub">
                                  {typeDocs.length}
                                </span>
                              )}
                            </div>

                            {/* Documents under Type */}
                            {isTypeOpen && (
                              <div className="tree-docs-container">
                                {typeDocs.length > 0 ? (
                                  typeDocs.map((doc) => {
                                    const isSelected =
                                      selectedDocId === doc.id;

                                    return (
                                      <div
                                        key={doc.id}
                                        className={`tree-doc-item ${
                                          isSelected ? "active" : ""
                                        }`}
                                        onClick={() => onSelectDocument(doc)}
                                        title={`Click to chat with ${doc.filename}`}
                                      >
                                        <FileText
                                          size={14}
                                          className={`doc-icon ${
                                            isSelected ? "active-icon" : ""
                                          }`}
                                        />
                                        <div className="doc-info">
                                          <span className="doc-name">
                                            {doc.filename}
                                          </span>
                                        </div>
                                        <div className="doc-actions">
                                          {doc.status === "ready" ? (
                                            <CheckCircle2
                                              size={13}
                                              className="text-success"
                                              title="Ready for QA"
                                            />
                                          ) : doc.status === "processing" ? (
                                            <Clock
                                              size={13}
                                              className="text-warning"
                                              title="Indexing..."
                                            />
                                          ) : (
                                            <AlertCircle
                                              size={13}
                                              className="text-danger"
                                              title="Error indexing"
                                            />
                                          )}
                                          <button
                                            className="btn-icon-xs text-danger"
                                            onClick={(e) => {
                                              e.stopPropagation();
                                              onDeleteDocument(doc.id);
                                            }}
                                            title="Delete document"
                                          >
                                            <Trash2 size={12} />
                                          </button>
                                        </div>
                                      </div>
                                    );
                                  })
                                ) : (
                                  <span className="empty-sub-hint">
                                    No documents
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })
                    ) : (
                      <span className="empty-sub-hint">No types created</span>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
