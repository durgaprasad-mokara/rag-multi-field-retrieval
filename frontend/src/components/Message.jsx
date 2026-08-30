import React from "react";
import ReactMarkdown from "react-markdown";
import { User, Sparkles } from "lucide-react";
import Source from "./Source";

export default function Message({ message }) {
  const { role, content, sources } = message;

  return (
    <div className={`message ${role}`}>
      <div className="message-avatar">
        {role === "user" ? <User size={16} /> : <Sparkles size={16} />}
      </div>
      <div className="message-body">
        <div className="message-content">
          {role === "assistant" ? (
            <ReactMarkdown>{content}</ReactMarkdown>
          ) : (
            <span>{content}</span>
          )}
        </div>

        {/* Source citations (assistant only) */}
        {role === "assistant" && sources && sources.length > 0 && (
          <Source sources={sources} />
        )}
      </div>
    </div>
  );
}
