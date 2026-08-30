import React, { useState, useRef } from "react";
import {
  ArrowLeft,
  UploadCloud,
  FileText,
  Trash2,
  CheckCircle2,
  Clock,
  AlertCircle,
  MessageSquare,
  Sparkles,
  CheckSquare,
  Square,
  FileSpreadsheet,
  FileCode,
  File,
} from "lucide-react";
import { uploadDocument, deleteDocument } from "../services/api";

function getFileIcon(filename) {
  const ext = filename.split(".").pop().toLowerCase();
  if (["xls", "xlsx", "csv"].includes(ext)) return <FileSpreadsheet size={20} className="icon-excel" />;
  if (["html", "json", "md"].includes(ext)) return <FileCode size={20} className="icon-code" />;
  if (["doc", "docx"].includes(ext)) return <FileText size={20} className="icon-word" />;
  if (ext === "pdf") return <FileText size={20} className="icon-pdf" />;
  return <File size={20} className="icon-default" />;
}

export default function DocumentManager({
  category,
  type,
  documents,
  onBackToTypes,
  onStartChat,
  onDocumentUploaded,
  onDocumentDeleted,
  onError,
}) {
  const [selectedDocIds, setSelectedDocIds] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef(null);

  // Filter documents belonging ONLY to this Category and Type
  const scopedDocs = documents.filter(
    (d) => d.category_id === category.id && d.type_id === type.id
  );

  // Toggle selection
  const handleToggleDoc = (docId) => {
    setSelectedDocIds((prev) => {
      if (prev.includes(docId)) {
        return prev.filter((id) => id !== docId);
      } else {
        return [...prev, docId];
      }
    });
  };

  // Select all / deselect all
  const handleToggleAll = () => {
    if (selectedDocIds.length === scopedDocs.length) {
      setSelectedDocIds([]);
    } else {
      setSelectedDocIds(scopedDocs.map((d) => d.id));
    }
  };

  // Upload handler
  async function handleFiles(files) {
    if (!files || files.length === 0) return;
    setUploading(true);
    setProgress(0);

    try {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const newDoc = await uploadDocument(
          file,
          category.id,
          type.id,
          (pct) => setProgress(pct)
        );
        onDocumentUploaded(newDoc);
        // Automatically select newly uploaded document
        setSelectedDocIds((prev) => [...prev, newDoc.id]);
      }
    } catch (err) {
      onError(err.response?.data?.detail || "Document upload failed");
    } finally {
      setUploading(false);
      setProgress(0);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  }

  async function handleDelete(docId, filename, e) {
    e.stopPropagation();
    if (!window.confirm(`Delete document "${filename}"?`)) return;
    try {
      await deleteDocument(docId);
      setSelectedDocIds((prev) => prev.filter((id) => id !== docId));
      onDocumentDeleted(docId);
    } catch (err) {
      onError("Failed to delete document");
    }
  }

  const handleStartChat = () => {
    if (selectedDocIds.length === 0) return;
    const selectedDocuments = scopedDocs.filter((d) =>
      selectedDocIds.includes(d.id)
    );
    onStartChat(selectedDocuments);
  };

  return (
    <div className="doc-manager-container">
      {/* Header & Scoped Breadcrumb Navigation */}
      <div className="grid-header">
        <div>
          <button
            className="btn btn-secondary btn-sm btn-back"
            onClick={onBackToTypes}
          >
            <ArrowLeft size={14} /> Back to {category.name} Types
          </button>
          <div className="scope-headline-group">
            <h2 className="grid-main-title">
              {category.name} &gt; {type.name} Documents
            </h2>
            <p className="grid-main-subtitle">
              Upload documents or select one to lock your RAG chat session strictly to this knowledge scope
            </p>
          </div>
        </div>
      </div>

      <div className="doc-manager-layout">
        {/* Left Side: Upload Card Scoped to Category & Type */}
        <div className="doc-upload-panel">
          <div className="upload-scope-card">
            <h4>Upload to {type.name}</h4>
            <p className="upload-scope-sub">
              Target Scope: <strong>{category.name} / {type.name}</strong>
            </p>

            <div
              className={`scoped-dropzone ${dragging ? "drag-over" : ""} ${
                uploading ? "disabled" : ""
              }`}
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
              onClick={() => !uploading && fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.docx,.doc,.txt,.md,.csv,.xlsx,.xls,.html,.htm,.json"
                style={{ display: "none" }}
                onChange={(e) => handleFiles(e.target.files)}
              />

              <div className="dropzone-icon">
                <UploadCloud size={32} />
              </div>

              {uploading ? (
                <div className="upload-progress-container">
                  <p className="upload-status-text">
                    Chunking &amp; Indexing into Vector DB...
                  </p>
                  <div className="progress-bar-bg">
                    <div
                      className="progress-bar-fill"
                      style={{ width: `${progress || 60}%` }}
                    />
                  </div>
                </div>
              ) : (
                <>
                  <p className="dropzone-title">
                    Drop files here, or <span className="browse-link">browse</span>
                  </p>
                  <p className="dropzone-sub">
                    PDF, DOCX, TXT, MD, CSV, XLSX, HTML
                  </p>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Right Side: Scoped Documents List & Chat Launcher */}
        <div className="doc-list-panel">
          <div className="doc-list-header">
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <h3>Available Documents ({scopedDocs.length})</h3>
              {scopedDocs.length > 0 && (
                <button
                  type="button"
                  className="btn-link"
                  onClick={handleToggleAll}
                >
                  {selectedDocIds.length === scopedDocs.length
                    ? "Deselect All"
                    : "Select All"}
                </button>
              )}
            </div>

            {selectedDocIds.length > 0 && (
              <button
                className="btn btn-primary btn-sm btn-start-chat-pulse"
                onClick={handleStartChat}
              >
                <Sparkles size={15} /> Start Chat ({selectedDocIds.length} Selected)
              </button>
            )}
          </div>

          <div className="scoped-docs-list">
            {scopedDocs.length > 0 ? (
              scopedDocs.map((doc) => {
                const isSelected = selectedDocIds.includes(doc.id);

                return (
                  <div
                    key={doc.id}
                    className={`scoped-doc-row ${isSelected ? "selected" : ""}`}
                    onClick={() => handleToggleDoc(doc.id)}
                  >
                    <div className="doc-checkbox">
                      {isSelected ? (
                        <CheckSquare size={18} className="text-accent" />
                      ) : (
                        <Square size={18} className="text-muted" />
                      )}
                    </div>

                    <div className="doc-file-icon">
                      {getFileIcon(doc.filename)}
                    </div>

                    <div className="doc-row-details">
                      <div className="doc-row-title-line">
                        <span className="doc-row-filename">{doc.filename}</span>
                        {isSelected && (
                          <span className="badge-selected-pill">Ready for Chat</span>
                        )}
                      </div>
                      <div className="doc-row-meta">
                        <span>{(doc.file_size / 1024).toFixed(1)} KB</span>
                        <span>•</span>
                        <span>{doc.chunk_count || 0} chunks</span>
                        <span>•</span>
                        <span>{new Date(doc.uploaded_at).toLocaleDateString()}</span>
                      </div>
                    </div>

                    <div className="doc-row-actions">
                      {doc.status === "ready" ? (
                        <CheckCircle2 size={16} className="text-success" title="Indexed & Ready" />
                      ) : doc.status === "processing" ? (
                        <Clock size={16} className="text-warning" title="Indexing..." />
                      ) : (
                        <AlertCircle size={16} className="text-danger" title="Error" />
                      )}

                      <button
                        className="btn-icon text-danger"
                        onClick={(e) => handleDelete(doc.id, doc.filename, e)}
                        title="Delete Document"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="empty-docs-box">
                <FileText size={42} className="empty-icon" />
                <h4>No documents in {type.name} yet</h4>
                <p>
                  Upload your first {type.name} document using the dropzone on the left to start chatting.
                </p>
              </div>
            )}
          </div>

          {/* Sticky Bottom Action Bar when items selected */}
          {selectedDocIds.length > 0 && (
            <div className="doc-floating-action-bar">
              <div className="action-bar-text">
                <strong>{selectedDocIds.length} document{selectedDocIds.length !== 1 ? "s" : ""} selected</strong>
                <span>Scope: {category.name} &gt; {type.name}</span>
              </div>
              <button
                className="btn btn-primary"
                onClick={handleStartChat}
              >
                <MessageSquare size={16} /> Start Chat with Selected Document{selectedDocIds.length !== 1 ? "s" : ""}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
