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

        {/* Response Performance Metric Badge (assistant only) */}
        {role === "assistant" && (message.responseTimeMs != null || message.response_time_ms != null) && (
          <div className="message-perf-badge">
            <span className="perf-time">
              ⏱ {((message.responseTimeMs ?? message.response_time_ms) / 1000).toFixed(2)}s
            </span>
            <span className="perf-divider">|</span>
            <span className="perf-target">
              🎯 Target: {((message.targetResponseTimeMs ?? message.target_response_time_ms ?? 2000) / 1000).toFixed(1).replace(".0", "")}s
            </span>
            <span className="perf-divider">|</span>
            <span className={`perf-status ${(message.withinTarget ?? message.within_target) ? "within" : "exceeded"}`}>
              {(message.withinTarget ?? message.within_target) ? "✓ Within target" : "⚠ Target exceeded"}
            </span>
          </div>
        )}

        {/* Source citations (assistant only) */}
        {role === "assistant" && sources && sources.length > 0 && (
          <Source sources={sources} />
        )}
      </div>
    </div>
  );
}
