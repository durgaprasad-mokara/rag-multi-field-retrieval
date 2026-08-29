import React, { useState, useRef, useEffect } from "react";
import { Send, Sparkles, MessageSquare, Trash2 } from "lucide-react";
import Message from "./Message";
import { sendMessage, getChatHistory, clearChatHistory } from "../services/api";

export default function Chat({ selectedDocId, hasDocuments, onError }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Load persistent chat history from PostgreSQL on mount / document filter change
  useEffect(() => {
    loadHistory();
  }, [selectedDocId]);

  async function loadHistory() {
    try {
      const history = await getChatHistory(selectedDocId);
      const formatted = [];
      history.forEach((msg) => {
        formatted.push({ role: "user", content: msg.question });
        formatted.push({
          role: "assistant",
          content: msg.answer,
          sources: msg.sources || [],
        });
      });
      setMessages(formatted);
    } catch (err) {
      console.error("Failed to load chat history:", err);
    }
  }

  async function handleClearHistory() {
    try {
      await clearChatHistory();
      setMessages([]);
    } catch (err) {
      onError("Failed to clear chat history.");
    }
  }

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSend(e) {
    e.preventDefault();
    const question = input.trim();
    if (!question || loading) return;

    // Add user message
    const userMsg = { role: "user", content: question };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const response = await sendMessage(question, selectedDocId);
      const assistantMsg = {
        role: "assistant",
        content: response.answer,
        sources: response.sources || [],
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const errorDetail =
        err.response?.data?.detail || "Failed to get a response. Please try again.";
      onError(errorDetail);
      // Add error message to chat
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Sorry, I encountered an error processing your request. Please try again.",
          sources: [],
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="chat-container">
      {/* ── Header ───────────────────────────────────── */}
      <div className="chat-header">
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <Sparkles size={20} className="chat-header-icon" />
          <div>
            <h2>Chat with your documents</h2>
            <span>
              {selectedDocId
                ? "Searching in selected document"
                : "Searching across all documents"}
            </span>
          </div>
        </div>

        {messages.length > 0 && (
          <button
            className="btn btn-secondary btn-sm"
            onClick={handleClearHistory}
            title="Clear chat history"
            style={{ marginLeft: "auto" }}
          >
            <Trash2 size={15} /> Clear History
          </button>
        )}
      </div>

      {/* ── Messages ─────────────────────────────────── */}
      <div className="chat-messages">
        {messages.length === 0 && !loading ? (
          <div className="chat-empty">
            <div className="chat-empty-icon">
              <MessageSquare size={28} />
            </div>
            <h3>Start a conversation</h3>
            <p>
              {hasDocuments
                ? "Ask any question about your uploaded documents. I'll find the most relevant information and provide a detailed answer."
                : "Upload a document first, then ask questions about it here."}
            </p>
          </div>
        ) : (
          <>
            {messages.map((msg, i) => (
              <Message key={i} message={msg} />
            ))}

            {/* Loading indicator */}
            {loading && (
              <div className="message assistant">
                <div className="message-avatar">
                  <Sparkles size={16} />
                </div>
                <div className="message-content">
                  <div className="loading-dots">
                    <span />
                    <span />
                    <span />
                  </div>
                </div>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* ── Input Bar ────────────────────────────────── */}
      <div className="chat-input-container">
        <form className="chat-input-wrapper" onSubmit={handleSend}>
          <input
            type="text"
            placeholder={
              hasDocuments
                ? "Ask a question about your documents…"
                : "Upload a document to start chatting…"
            }
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <button
            type="submit"
            className="send-btn"
            disabled={!input.trim() || loading}
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}
