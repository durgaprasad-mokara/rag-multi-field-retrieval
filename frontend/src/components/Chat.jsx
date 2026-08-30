import React, { useState, useRef, useEffect } from "react";
import {
  Send,
  Sparkles,
  MessageSquare,
  Trash2,
  FileText,
  Briefcase,
  Folder,
  SlidersHorizontal,
  FileUp,
  Database,
  HelpCircle,
  Award,
  ShieldAlert,
} from "lucide-react";
import Message from "./Message";
import {
  sendMessage,
  getChatHistory,
  clearChatHistory,
  createChatSession,
} from "../services/api";

export default function Chat({ activeCategory, activeType, activeDocument, onError }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const messagesEndRef = useRef(null);

  // Reinitialise session when active document changes
  useEffect(() => {
    if (activeDocument) {
      initSession();
    } else {
      setMessages([]);
      setSessionId(null);
    }
  }, [activeDocument?.id]);

  async function initSession() {
    if (!activeDocument) return;
    try {
      const session = await createChatSession(activeDocument.id);
      setSessionId(session.id);
      const history = await getChatHistory(session.id, activeDocument.id);
      const formatted = [];
      history.forEach((msg) => {
        if (msg.role === "user") {
          formatted.push({ role: "user", content: msg.question || msg.answer });
        } else {
          formatted.push({ role: "assistant", content: msg.answer, sources: msg.sources || [] });
        }
      });
      setMessages(formatted);
    } catch (err) {
      console.error("Session init failed:", err);
    }
  }

  async function handleClearHistory() {
    if (!sessionId || !activeDocument) return;
    try {
      await clearChatHistory(sessionId, activeDocument.id);
      setMessages([]);
    } catch {
      onError("Failed to clear chat history.");
    }
  }

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSend(e) {
    e.preventDefault();
    const q = input.trim();
    if (!q || loading) return;
    if (!activeDocument) {
      onError("Please select a category, choose a type, then upload a document to start chatting.");
      return;
    }

    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setInput("");
    setLoading(true);

    try {
      const res = await sendMessage(q, sessionId, activeDocument.id);
      if (res.session_id && !sessionId) setSessionId(res.session_id);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.answer, sources: res.sources || [] },
      ]);
    } catch (err) {
      onError(err.response?.data?.detail || "Failed to get a response.");
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Sorry, an error occurred.", sources: [] },
      ]);
    } finally {
      setLoading(false);
    }
  }

  const isEmpty = messages.length === 0 && !loading;

  return (
    <div className="main-chat-container">

      {/* ── Top Header ───────────────────────────────────────── */}
      <header className="chat-top-header">
        <div className="chat-header-title-block">
          <div className="chat-header-icon-box">
            <FileText size={16} className="text-purple" />
          </div>
          <div className="chat-header-text">
            <h2 className="chat-main-heading">Chat with your documents</h2>
            <p className="chat-main-subheading">
              {activeDocument
                ? `Searching in: ${activeCategory?.name ?? ""} › ${activeType?.name ?? ""}`
                : "Upload a document under any category to start asking questions."}
            </p>
          </div>
        </div>
        <button className="btn-clear-history" onClick={handleClearHistory} title="Clear chat history">
          <Trash2 size={13} />
          Clear History
        </button>
      </header>

      {/* ── Scroll Area ───────────────────────────────────────── */}
      <div className="chat-scroll-area">

        {isEmpty ? (
          /* ── Empty State Dashboard ──────────────────────── */
          <div className="empty-state-full-layout">

            {/* Scope Context Card */}
            <div className="scope-selection-top-badge">
              <div className="badge-col">
                <span className="badge-label">
                  <Briefcase size={11} className="text-purple" />
                  Selected Category:
                </span>
                <span className="badge-value-purple">
                  {activeCategory?.name || "None selected"}
                </span>
              </div>
              <div className="badge-divider" />
              <div className="badge-col">
                <span className="badge-label">Selected Type:</span>
                <span className="badge-value-purple">
                  {activeType?.name || "None selected"}
                </span>
              </div>
              <div className="badge-divider" />
              <div className="badge-col">
                <span className="badge-label">Document:</span>
                <span className="badge-value-muted">
                  {activeDocument ? activeDocument.filename : "No document uploaded"}
                </span>
              </div>
            </div>

            {/* 2-Column: Center Welcome + Right How-to-Use */}
            <div className="empty-state-middle-grid">

              {/* Left: Welcome */}
              <div className="center-welcome-panel">
                <div className="empty-state-purple-circle">
                  <MessageSquare size={28} className="empty-state-bubble-icon" />
                </div>
                <h3 className="empty-state-headline">Start a conversation</h3>
                <p className="empty-state-paragraph">
                  Upload a document under a selected category and type, then ask
                  questions about the document. Answers are generated strictly from
                  the selected document.
                </p>

                {/* How it works strip */}
                <div className="how-it-works-inline-strip">
                  <span className="how-it-works-label">How it works:</span>
                  <div className="step-tag"><span className="step-dot">1</span>Select Category</div>
                  <div className="step-tag"><span className="step-dot">2</span>Select Type</div>
                  <div className="step-tag"><span className="step-dot">3</span>Upload Document</div>
                  <div className="step-tag"><span className="step-dot">4</span>Ask Questions</div>
                  <div className="step-tag"><span className="step-dot">5</span>Get Answers</div>
                </div>
              </div>

              {/* Right: How to use */}
              <div className="how-to-use-guide-card">
                <h4 className="guide-card-title">How to use</h4>
                <ol className="guide-steps-list">
                  <li>
                    <span className="guide-num">1</span>
                    <span>Select a category from the left panel.</span>
                  </li>
                  <li>
                    <span className="guide-num">2</span>
                    <span>Choose a relevant type under that category.</span>
                  </li>
                  <li>
                    <span className="guide-num">3</span>
                    <span>
                      Click <strong>Browse Files</strong> or drag &amp; drop your document.
                    </span>
                  </li>
                  <li>
                    <span className="guide-num">4</span>
                    <span>Ask any question related to the uploaded document.</span>
                  </li>
                  <li>
                    <span className="guide-num">5</span>
                    <span>Get precise answers with page-level source citations.</span>
                  </li>
                </ol>

                <div className="guide-important-alert">
                  <div className="alert-shield-row">
                    <ShieldAlert size={13} className="text-warning" />
                    <strong>Important</strong>
                  </div>
                  <p>
                    Answers are generated strictly from the selected document only.
                  </p>
                </div>
              </div>
            </div>
          </div>

        ) : (
          /* ── Active Chat Messages ────────────────────────── */
          <div className="chat-messages-flow">
            {messages.map((msg, i) => (
              <Message key={i} message={msg} />
            ))}

            {loading && (
              <div className="message assistant">
                <div className="message-avatar">
                  <Sparkles size={14} />
                </div>
                <div className="message-content">
                  <div className="loading-dots">
                    <span /><span /><span />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* ── Bottom Bar: Input + RAG Flow Strip ───────────────── */}
      <div className="chat-bottom-bar">

        {/* Chat Input */}
        <form onSubmit={handleSend} className="chat-input-wrapper">
          <input
            type="text"
            className="input-chat-query"
            placeholder={
              activeDocument
                ? `Ask a question about ${activeDocument.filename}...`
                : "Ask a question about your document..."
            }
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <button
            type="submit"
            className="btn-send-airplane"
            disabled={!input.trim() || loading}
            title="Send"
          >
            <Send size={15} />
          </button>
        </form>

        {/* Document Ingestion & RAG Flow */}
        <div className="document-rag-flow-strip">
          <p className="rag-flow-title">Document Ingestion &amp; RAG Flow</p>
          <div className="rag-flow-steps-row">

            <div className="flow-step-box">
              <div className="flow-step-icon"><Folder size={13} /></div>
              <div className="flow-step-text">
                <strong>1. Select Category</strong>
                <span>Choose a main category from the left panel</span>
              </div>
            </div>

            <span className="flow-arrow">→</span>

            <div className="flow-step-box">
              <div className="flow-step-icon"><SlidersHorizontal size={13} /></div>
              <div className="flow-step-text">
                <strong>2. Select Type</strong>
                <span>Choose a relevant type under the category</span>
              </div>
            </div>

            <span className="flow-arrow">→</span>

            <div className="flow-step-box">
              <div className="flow-step-icon"><FileUp size={13} /></div>
              <div className="flow-step-text">
                <strong>3. Upload Document</strong>
                <span>Upload your document using browser or drag &amp; drop</span>
              </div>
            </div>

            <span className="flow-arrow">→</span>

            <div className="flow-step-box">
              <div className="flow-step-icon"><Database size={13} /></div>
              <div className="flow-step-text">
                <strong>4. Process &amp; Index</strong>
                <span>Document is chunked, embedded &amp; stored</span>
              </div>
            </div>

            <span className="flow-arrow">→</span>

            <div className="flow-step-box">
              <div className="flow-step-icon"><HelpCircle size={13} /></div>
              <div className="flow-step-text">
                <strong>5. Ask Questions</strong>
                <span>Ask anything related to the document</span>
              </div>
            </div>

            <span className="flow-arrow">→</span>

            <div className="flow-step-box">
              <div className="flow-step-icon"><Award size={13} /></div>
              <div className="flow-step-text">
                <strong>6. Get Answers</strong>
                <span>Get exact answers with source citations</span>
              </div>
            </div>

          </div>
        </div>

      </div>
    </div>
  );
}
