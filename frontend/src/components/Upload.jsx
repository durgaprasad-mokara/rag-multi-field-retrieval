import React, { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload as UploadIcon, FileText, Trash2 } from "lucide-react";
import { uploadDocument, deleteDocument } from "../services/api";

const ACCEPT = {
  "application/pdf": [".pdf"],
  "text/plain": [".txt"],
  "text/markdown": [".md"],
  "text/csv": [".csv"],
  "text/html": [".html"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [
    ".docx",
  ],
};

function formatBytes(bytes) {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

export default function Upload({
  onUploadComplete,
  onDocumentDeleted,
  onError,
  documents,
}) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);

  const onDrop = useCallback(
    async (acceptedFiles) => {
      if (acceptedFiles.length === 0) return;

      const file = acceptedFiles[0];
      setUploading(true);
      setProgress(0);

      try {
        const doc = await uploadDocument(file, (p) => setProgress(p));
        onUploadComplete(doc);
      } catch (err) {
        const msg =
          err.response?.data?.detail || "Upload failed. Please try again.";
        onError(msg);
      } finally {
        setUploading(false);
        setProgress(0);
      }
    },
    [onUploadComplete, onError]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPT,
    multiple: false,
    disabled: uploading,
  });

  async function handleDelete(e, docId) {
    e.stopPropagation();
    try {
      await deleteDocument(docId);
      onDocumentDeleted(docId);
    } catch (err) {
      onError("Failed to delete document.");
    }
  }

  return (
    <>
      {/* ── Drop Zone ──────────────────────────────────── */}
      <div
        {...getRootProps()}
        className={`upload-zone ${isDragActive ? "active" : ""}`}
      >
        <input {...getInputProps()} />
        <UploadIcon size={28} className="upload-icon" />
        <h3>{uploading ? "Uploading…" : "Drop a document here"}</h3>
        <p>PDF, TXT, DOCX, Markdown, CSV, HTML</p>

        {uploading && (
          <div className="upload-progress">
            <div className="progress-bar">
              <div
                className="progress-fill"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="progress-text">{progress}% uploaded</div>
          </div>
        )}
      </div>

      {/* ── Document List ──────────────────────────────── */}
      {documents.length > 0 && (
        <>
          <div className="document-list-title">
            Documents ({documents.length})
          </div>
          {documents.map((doc) => (
            <div key={doc.id} className="document-item">
              <FileText size={18} className="document-icon" />
              <div className="document-info">
                <div className="document-name">{doc.filename}</div>
                <div className="document-meta">
                  {formatBytes(doc.file_size)} · {doc.chunk_count} chunks
                </div>
              </div>
              <span className={`status-badge ${doc.status}`}>
                {doc.status}
              </span>
              <button
                className="delete-btn"
                onClick={(e) => handleDelete(e, doc.id)}
                title="Delete document"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </>
      )}

      {documents.length === 0 && !uploading && (
        <div className="no-documents">
          No documents uploaded yet. Drop a file above to get started.
        </div>
      )}
    </>
  );
}
