import React, { useState, useRef, useEffect } from "react";
import {
  Send,
  Sparkles,
  Trash2,
  FileText,
  Mic,
  MicOff,
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
  const [isRecording, setIsRecording] = useState(false);
  const [voiceLang, setVoiceLang] = useState("en-US");
  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);

  // Web Speech API browser feature detection
  const isSpeechSupported =
    typeof window !== "undefined" &&
    ("SpeechRecognition" in window || "webkitSpeechRecognition" in window);

  // Clean up speech recognition on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // Ignore cleanup errors
        }
      }
    };
  }, []);

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

  // Voice recording toggle handler
  function toggleVoiceInput() {
    if (!isSpeechSupported) {
      onError("Voice input is not supported in this browser. Please use typing.");
      return;
    }

    if (isRecording) {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {
          // Ignore
        }
      }
      setIsRecording(false);
      return;
    }

    try {
      const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognition = new SpeechRecognition();

      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.maxAlternatives = 1;
      recognition.lang = voiceLang;

      recognition.onstart = () => {
        setIsRecording(true);
      };

      recognition.onresult = (event) => {
        let transcript = "";
        for (let i = 0; i < event.results.length; i++) {
          transcript += event.results[i][0].transcript;
        }
        if (transcript) {
          setInput(transcript);
        }
      };

      recognition.onerror = (event) => {
        setIsRecording(false);
        let msg = "Unable to recognize speech. Please try again.";
        if (event.error === "not-allowed") {
          msg = "Microphone access was denied. Please allow microphone access or use typing.";
        } else if (event.error === "no-speech") {
          msg = "No speech detected. Please try again.";
        } else if (event.error === "audio-capture") {
          msg = "No microphone was found or microphone is busy.";
        } else if (event.error === "network") {
          msg = "Network error during speech recognition. Please try again.";
        } else if (event.error === "aborted") {
          return;
        }
        onError(msg);
      };

      recognition.onend = () => {
        setIsRecording(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      console.error("Speech recognition error:", err);
      setIsRecording(false);
      onError("Unable to initialize speech recognition. Please use typing.");
    }
  }

  async function handleSend(e) {
    e.preventDefault();
    const q = input.trim();
    if (!q || loading) return;
    if (!activeDocument) {
      onError("Please select a category, choose a type, then upload a document to start chatting.");
      return;
    }

    // Stop voice recording if active when sending
    if (isRecording && recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // Ignore
      }
      setIsRecording(false);
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
            <div className="chat-header-context-bar">
              <div className="context-bar-item">
                <span className="context-label">Category:</span>
                <span className={`context-val ${activeCategory ? "highlight" : "muted"}`}>
                  {activeCategory?.name || "Not selected"}
                </span>
              </div>
              <span className="context-bar-sep">|</span>
              <div className="context-bar-item">
                <span className="context-label">Type:</span>
                <span className={`context-val ${activeType ? "highlight" : "muted"}`}>
                  {activeType?.name || "Not selected"}
                </span>
              </div>
              <span className="context-bar-sep">|</span>
              <div className="context-bar-item file-item">
                <span className="context-label">File:</span>
                <span
                  className={`context-val ${activeDocument ? "highlight file-name" : "muted"}`}
                  title={activeDocument?.filename || "No document uploaded"}
                >
                  {activeDocument ? activeDocument.filename : "No document uploaded"}
                </span>
              </div>
            </div>
          </div>
        </div>
        <button className="btn-clear-history" onClick={handleClearHistory} title="Clear chat history">
          <Trash2 size={13} />
          Clear History
        </button>
      </header>

      {/* ── Scroll Area ───────────────────────────────────────── */}
      <div className="chat-scroll-area">

        {!isEmpty && (
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

      {/* ── Bottom Bar: Input ─────────────────────────────────── */}
      <div className="chat-bottom-bar">

        {/* Chat Input with Voice Button */}
        <form onSubmit={handleSend} className="chat-input-wrapper">
          <button
            type="button"
            className={`btn-mic-voice ${isRecording ? "recording" : ""}`}
            onClick={toggleVoiceInput}
            disabled={loading || !isSpeechSupported}
            aria-label={isRecording ? "Stop voice input" : "Start voice input"}
            title={
              !isSpeechSupported
                ? "Voice input is not supported in this browser. Please use typing."
                : isRecording
                ? "Listening... Click to stop"
                : "Use voice input"
            }
          >
            {isRecording ? <MicOff size={16} /> : <Mic size={16} />}
          </button>

          <input
            type="text"
            className="input-chat-query"
            placeholder={
              isRecording
                ? "Listening... Speak your question..."
                : activeDocument
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
      </div>
    </div>
  );
}
