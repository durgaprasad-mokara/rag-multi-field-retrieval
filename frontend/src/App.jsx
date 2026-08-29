import React, { useState, useEffect } from "react";
import { MessageSquare, AlertCircle } from "lucide-react";
import Upload from "./components/Upload";
import Chat from "./components/Chat";
import { getDocuments } from "./services/api";

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState(null);
  const [error, setError] = useState(null);

  // Fetch documents on mount
  useEffect(() => {
    fetchDocuments();
  }, []);

  // Auto-dismiss errors
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  async function fetchDocuments() {
    try {
      const docs = await getDocuments();
      setDocuments(docs);
    } catch (err) {
      console.error("Failed to fetch documents:", err);
    }
  }

  function handleUploadComplete(newDoc) {
    setDocuments((prev) => [newDoc, ...prev]);
  }

  function handleDocumentDeleted(docId) {
    setDocuments((prev) => prev.filter((d) => d.id !== docId));
    if (selectedDocId === docId) {
      setSelectedDocId(null);
    }
  }

  const readyDocs = documents.filter((d) => d.status === "ready");

  return (
    <div className="app">
      {/* ── Sidebar ──────────────────────────────────────── */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1>
            <MessageSquare size={22} />
            RAG Assistant
          </h1>
          <p>Upload documents &amp; chat with AI</p>
        </div>

        <div className="sidebar-content">
          <Upload
            onUploadComplete={handleUploadComplete}
            onDocumentDeleted={handleDocumentDeleted}
            onError={setError}
            documents={documents}
          />
        </div>

        {/* Document filter */}
        {readyDocs.length > 0 && (
          <div className="document-filter">
            <label>Chat scope</label>
            <select
              value={selectedDocId ?? ""}
              onChange={(e) =>
                setSelectedDocId(e.target.value ? Number(e.target.value) : null)
              }
            >
              <option value="">All documents</option>
              {readyDocs.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.filename}
                </option>
              ))}
            </select>
          </div>
        )}
      </aside>

      {/* ── Main Panel ───────────────────────────────────── */}
      <main className="main-panel">
        <Chat
          selectedDocId={selectedDocId}
          hasDocuments={readyDocs.length > 0}
          onError={setError}
        />
      </main>

      {/* ── Error Toast ──────────────────────────────────── */}
      {error && (
        <div className="error-toast">
          <AlertCircle size={18} className="error-icon" />
          {error}
        </div>
      )}
    </div>
  );
}
