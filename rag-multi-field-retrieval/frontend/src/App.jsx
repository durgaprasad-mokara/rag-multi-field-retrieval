import React, { useState, useEffect } from "react";
import { AlertCircle } from "lucide-react";
import SidebarHierarchy from "./components/SidebarHierarchy";
import Chat from "./components/Chat";
import { getCategories } from "./services/api";

export default function App() {
  // ── Navigation State (categories + types hierarchy) ───────────────────────
  const [categories, setCategories] = useState([]);
  const [activeCategory, setActiveCategory] = useState(null);
  const [activeType, setActiveType] = useState(null);

  // ── Document/RAG State (internal only, NEVER used for sidebar nav) ─────────
  const [activeDocument, setActiveDocument] = useState(null);

  // ── UI State ──────────────────────────────────────────────────────────────
  const [error, setError] = useState(null);

  // Fetch only category taxonomy on mount — NO document fetching for sidebar
  useEffect(() => {
    fetchCategories();
  }, []);

  // Auto-dismiss errors after 6 seconds
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 6000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  async function fetchCategories() {
    try {
      const catsData = await getCategories();
      setCategories(catsData);

      // Default open the first category (Company) — do NOT auto-select any document
      const companyCat =
        catsData.find((c) => c.name.toLowerCase().includes("company")) ||
        catsData[0];
      if (companyCat) {
        setActiveCategory(companyCat);
        // No auto-type selection, no document lookup
      }
    } catch (err) {
      console.error("Failed to load categories:", err);
      setError(
        "Failed to connect to backend server. Please verify services are running."
      );
    }
  }

  async function refreshCategories() {
    try {
      const catsData = await getCategories();
      setCategories(catsData);
      if (activeCategory) {
        const updated = catsData.find((c) => c.id === activeCategory.id);
        if (updated) setActiveCategory(updated);
      }
    } catch (err) {
      console.error("Failed to refresh categories:", err);
    }
  }

  // ── Navigation Handlers ────────────────────────────────────────────────────
  // IMPORTANT: Selecting a category or type does NOT activate any document.
  // Documents are activated ONLY when the user explicitly uploads a file.

  const handleSelectCategory = (cat) => {
    setActiveCategory(cat);
    setActiveType(null);
    // Never auto-select a document when a category is clicked
    setActiveDocument(null);
  };

  const handleSelectType = (type) => {
    setActiveType(type);
    // Never auto-select a document when a type is clicked
    // The user must upload a file to activate a document
    setActiveDocument(null);
  };

  // ── Upload Handler ─────────────────────────────────────────────────────────
  // Called by SidebarHierarchy after a successful upload.
  // Sets the active document for chat — but NEVER modifies sidebar navigation.
  const handleDocumentUploaded = (newDoc, cat, type) => {
    // Update navigation scope to match the uploaded document
    setActiveCategory(cat);
    setActiveType(type);
    // Set the uploaded document as the active RAG document
    setActiveDocument(newDoc);
    // Refresh category counts (document_count badge in types)
    refreshCategories();
  };

  return (
    <div className="app">
      {/* ── Left Sidebar: ONLY Categories & Types, NEVER filenames ── */}
      <SidebarHierarchy
        categories={categories}
        activeCategory={activeCategory}
        activeType={activeType}
        onSelectCategory={handleSelectCategory}
        onSelectType={handleSelectType}
        onDocumentUploaded={handleDocumentUploaded}
        onError={setError}
      />

      {/* ── Main Chat Area ────────────────────────────────────────── */}
      <main className="main-panel">
        <Chat
          activeCategory={activeCategory}
          activeType={activeType}
          activeDocument={activeDocument}
          onError={setError}
        />
      </main>

      {/* ── Error Toast ──────────────────────────────────────────── */}
      {error && (
        <div className="error-toast">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
