import React, { useState, useRef, useEffect } from "react";
import {
  Send,
  Sparkles,
  Trash2,
  FileText,
  Mic,
  MicOff,
  Volume2,
  VolumeX,
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
  const [voiceResponseEnabled, setVoiceResponseEnabled] = useState(true); // Default ON
  const [targetResponseTime, setTargetResponseTime] = useState(2.0);
  const [liveTimer, setLiveTimer] = useState("0.00");

  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);
  const inputRef = useRef(input);
  inputRef.current = input;

  // Web Speech API browser feature detection
  const isSpeechSupported =
    typeof window !== "undefined" &&
    ("SpeechRecognition" in window || "webkitSpeechRecognition" in window);

  const isTtsSupported =
    typeof window !== "undefined" && "speechSynthesis" in window;

  // Live timer for real response-time measurement
  useEffect(() => {
    let timerInterval = null;
    if (loading) {
      const t0 = performance.now();
      timerInterval = setInterval(() => {
        const elapsed = ((performance.now() - t0) / 1000).toFixed(2);
        setLiveTimer(elapsed);
      }, 50);
    } else {
      setLiveTimer("0.00");
    }
    return () => {
      if (timerInterval) clearInterval(timerInterval);
    };
  }, [loading]);

  // Clean up speech recognition & synthesis on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // Ignore cleanup errors
        }
      }
      if (typeof window !== "undefined" && window.speechSynthesis) {
        window.speechSynthesis.cancel();
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
          formatted.push({
            role: "assistant",
            content: msg.answer,
            sources: msg.sources || [],
            responseTimeMs: msg.response_time_ms,
            targetResponseTimeMs: msg.target_response_time_ms,
            withinTarget: msg.within_target,
          });
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
      if (typeof window !== "undefined" && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
      await clearChatHistory(sessionId, activeDocument.id);
      setMessages([]);
    } catch {
      onError("Failed to clear chat history.");
    }
  }

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  // ── Text-to-Speech (TTS) Engine ──────────────────────────────
  function speakResponse(text) {
    if (!isTtsSupported || !voiceResponseEnabled) return;
    if (!text || !text.trim()) return;

    try {
      // Stop any prior playback immediately
      window.speechSynthesis.cancel();

      // Clean markdown tags & symbols for natural English speech
      let spokenText = text
        .replace(/###\s+/g, "")
        .replace(/[-*•]\s+/g, "")
        .replace(/\[\d{1,2}:\d{2}(?:–\d{1,2}:\d{2})?\]/g, "")
        .replace(/https?:\/\/\S+/g, "")
        .replace(/`{1,3}[^`]*`{1,3}/g, "")
        .replace(/\s+/g, " ")
        .trim();

      if (!spokenText) return;

      const utterance = new SpeechSynthesisUtterance(spokenText);
      utterance.lang = "en-US";
      utterance.rate = 1.0;
      utterance.pitch = 1.0;

      // Select an English voice if available
      const voices = window.speechSynthesis.getVoices();
      const englishVoice =
        voices.find(
          (v) =>
            v.lang.startsWith("en") &&
            (v.name.includes("Google") ||
              v.name.includes("Natural") ||
              v.name.includes("Samantha") ||
              v.name.includes("David") ||
              v.name.includes("Zira"))
        ) || voices.find((v) => v.lang.startsWith("en"));

      if (englishVoice) {
        utterance.voice = englishVoice;
      }

      window.speechSynthesis.speak(utterance);
    } catch (e) {
      console.error("Speech synthesis error:", e);
    }
  }

  // ── Unified Question Pipeline (Typing & Voice) ───────────────
  async function executeQuestion(questionText) {
    const q = questionText.trim();
    if (!q || loading) return;

    if (!activeDocument) {
      onError("Please select a category, choose a type, then upload a document to start chatting.");
      return;
    }

    // Interrupt any ongoing voice playback immediately
    if (typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }

    // Stop voice recording if still active
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

    const t0 = performance.now();

    try {
      const res = await sendMessage(q, sessionId, activeDocument.id, null, targetResponseTime);
      const clientDurationMs = Math.round(performance.now() - t0);

      if (res.session_id && !sessionId) setSessionId(res.session_id);

      const finalAnswer = res.answer;

      // 1. Render in Chat
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: finalAnswer,
          sources: res.sources || [],
          responseTimeMs: res.response_time_ms || clientDurationMs,
          targetResponseTimeMs: res.target_response_time_ms || (targetResponseTime * 1000),
          withinTarget:
            res.within_target !== undefined && res.within_target !== null
              ? res.within_target
              : clientDurationMs <= targetResponseTime * 1000,
        },
      ]);

      // 2. Speak the exact validated answer in English if voice output is ON
      speakResponse(finalAnswer);
    } catch (err) {
      const errorMsg = "Sorry, I couldn't process your request. Please try again.";
      onError(err.response?.data?.detail || errorMsg);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: errorMsg, sources: [] },
      ]);
      speakResponse(errorMsg);
    } finally {
      setLoading(false);
    }
  }

  function handleFormSubmit(e) {
    e.preventDefault();
    executeQuestion(input);
  }

  // ── Voice Recording Toggle Handler ───────────────────────────
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

    // Interrupt any ongoing voice playback before listening
    if (typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.cancel();
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
        if (event.error === "aborted") return;

        let msg = "I couldn't understand the question. Please try again.";
        if (event.error === "not-allowed") {
          msg = "Microphone access was denied. Please allow microphone access or use typing.";
        } else if (event.error === "no-speech") {
          msg = "I couldn't understand the question. Please try again.";
        }
        onError(msg);
        speakResponse(msg);
      };

      recognition.onend = () => {
        setIsRecording(false);
        const spokenQuestion = inputRef.current?.trim();
        if (spokenQuestion && activeDocument && !loading) {
          executeQuestion(spokenQuestion);
        }
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      console.error("Speech recognition error:", err);
      setIsRecording(false);
      onError("Unable to initialize speech recognition. Please use typing.");
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

        <div className="chat-header-actions" style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {/* Voice Response Control: ON / OFF */}
          <button
            type="button"
            className={`btn-voice-toggle ${voiceResponseEnabled ? "voice-on" : "voice-off"}`}
            onClick={() => {
              const nextVal = !voiceResponseEnabled;
              setVoiceResponseEnabled(nextVal);
              if (!nextVal && typeof window !== "undefined" && window.speechSynthesis) {
                window.speechSynthesis.cancel();
              }
            }}
            title={voiceResponseEnabled ? "Voice Response: ON (Click to mute)" : "Voice Response: OFF (Click to enable)"}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "5px",
              padding: "5px 10px",
              fontSize: "12px",
              fontWeight: 500,
              borderRadius: "6px",
              border: voiceResponseEnabled ? "1px solid rgba(56, 189, 248, 0.4)" : "1px solid rgba(255, 255, 255, 0.1)",
              background: voiceResponseEnabled ? "rgba(56, 189, 248, 0.15)" : "rgba(255, 255, 255, 0.05)",
              color: voiceResponseEnabled ? "#38bdf8" : "#94a3b8",
              cursor: "pointer",
              transition: "all 0.2s ease",
            }}
          >
            {voiceResponseEnabled ? <Volume2 size={13} /> : <VolumeX size={13} />}
            <span>Voice: {voiceResponseEnabled ? "ON" : "OFF"}</span>
          </button>

          <button className="btn-clear-history" onClick={handleClearHistory} title="Clear chat history">
            <Trash2 size={13} />
            Clear History
          </button>
        </div>
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
                <div className="message-content loading-bubble">
                  <div className="loading-dots">
                    <span /><span /><span />
                  </div>
                  <span className="live-timer-text">Generating answer... {liveTimer}s</span>
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
        <form onSubmit={handleFormSubmit} className="chat-input-wrapper">
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
