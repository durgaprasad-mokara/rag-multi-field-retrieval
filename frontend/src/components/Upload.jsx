import React, { useState, useRef } from "react";
import {
  UploadCloud,
  FileText,
  CheckCircle,
  AlertCircle,
  Plus,
  Layers,
} from "lucide-react";
import { uploadDocument } from "../services/api";

export default function Upload({
  categories,
  onUploadComplete,
  onOpenCategoryManager,
  onError,
}) {
  const [selectedCategoryId, setSelectedCategoryId] = useState(
    categories[0]?.id || ""
  );
  const [selectedTypeId, setSelectedTypeId] = useState("");
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [dragging, setDragging] = useState(false);
  const fileInputRef = useRef(null);

  // Derive available document types based on selected category
  const activeCategory = categories.find(
    (c) => c.id === Number(selectedCategoryId)
  );
  const availableTypes = activeCategory?.types || [];

  // Update selected type if category changes
  const handleCategoryChange = (e) => {
    const catId = Number(e.target.value);
    setSelectedCategoryId(catId);
    const cat = categories.find((c) => c.id === catId);
    if (cat?.types?.length > 0) {
      setSelectedTypeId(cat.types[0].id);
    } else {
      setSelectedTypeId("");
    }
  };

  // Set default type if not set
  React.useEffect(() => {
    if (availableTypes.length > 0 && !selectedTypeId) {
      setSelectedTypeId(availableTypes[0].id);
    }
  }, [availableTypes, selectedTypeId]);

  async function handleFiles(files) {
    if (!files || files.length === 0) return;

    if (!selectedCategoryId) {
      onError("Please select a Category before uploading.");
      return;
    }
    if (!selectedTypeId) {
      onError("Please select a Document Type before uploading.");
      return;
    }

    const file = files[0];
    setUploading(true);
    setProgress(0);

    try {
      const newDoc = await uploadDocument(
        file,
        Number(selectedCategoryId),
        Number(selectedTypeId),
        (pct) => setProgress(pct)
      );
      onUploadComplete(newDoc);
    } catch (err) {
      const errorMsg =
        err.response?.data?.detail ||
        "Upload failed. Please check file format and size.";
      onError(errorMsg);
    } finally {
      setUploading(false);
      setProgress(0);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  }

  return (
    <div className="upload-container">
      {/* ── Category & Type Pickers ─────────────────────── */}
      <div className="upload-selectors-card">
        <div className="selector-group">
          <div className="selector-header-row">
            <label>1. Select Category</label>
            <button
              type="button"
              className="btn-link"
              onClick={onOpenCategoryManager}
              title="Manage categories and types"
            >
              <Layers size={12} /> Manage
            </button>
          </div>
          <select
            value={selectedCategoryId}
            onChange={handleCategoryChange}
            disabled={uploading}
            className="select-custom"
          >
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.types?.length || 0} types)
              </option>
            ))}
          </select>
        </div>

        <div className="selector-group" style={{ marginTop: "10px" }}>
          <label>2. Select Document Type</label>
          {availableTypes.length > 0 ? (
            <select
              value={selectedTypeId}
              onChange={(e) => setSelectedTypeId(Number(e.target.value))}
              disabled={uploading}
              className="select-custom"
            >
              {availableTypes.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          ) : (
            <div className="no-types-warning">
              <span>No types in this category yet.</span>
              <button
                type="button"
                className="btn-link"
                onClick={onOpenCategoryManager}
              >
                <Plus size={11} /> Add type
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ── Dropzone ────────────────────────────────────── */}
      <div
        className={`dropzone ${dragging ? "drag-over" : ""} ${
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
          accept=".pdf,.docx,.doc,.txt,.md,.csv,.xlsx,.xls,.html,.htm,.json"
          style={{ display: "none" }}
          onChange={(e) => handleFiles(e.target.files)}
        />

        <div className="dropzone-icon">
          <UploadCloud size={28} />
        </div>

        {uploading ? (
          <div className="upload-progress-container">
            <p className="upload-status-text">Indexing with RAG pipeline...</p>
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
              Drop document here, or <span className="browse-link">browse</span>
            </p>
            <p className="dropzone-sub">
              PDF, DOCX, TXT, MD, CSV, XLSX, HTML
            </p>
          </>
        )}
      </div>
    </div>
  );
}
