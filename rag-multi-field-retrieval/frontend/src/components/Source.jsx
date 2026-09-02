import React, { useState } from "react";
import { ChevronDown, FileText, Video, Clock, Tag } from "lucide-react";

export default function Source({ sources }) {
  const [open, setOpen] = useState(false);

  if (!sources || sources.length === 0) return null;

  return (
    <div className="sources-container">
      <button className="sources-toggle" onClick={() => setOpen(!open)}>
        <FileText size={12} />
        {sources.length} source{sources.length !== 1 ? "s" : ""} cited
        <ChevronDown size={14} className={`chevron ${open ? "open" : ""}`} />
      </button>

      {open && (
        <div className="sources-list">
          {sources.map((src, i) => {
            const isVideo =
              Boolean(src.start_time) ||
              /\.(mp4|webm|mov|mkv|avi|m4v|flv)$/i.test(src.document_name || "");
            const tsLabel = src.start_time
              ? src.end_time
                ? `${src.start_time}–${src.end_time}`
                : src.start_time
              : null;

            return (
              <div key={i} className="source-item">
                <div className="source-name" style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
                  {isVideo ? <Video size={12} className="text-cyan" /> : <FileText size={11} />}
                  <span>{src.document_name}</span>
                  {tsLabel && (
                    <span className="source-timestamp-pill" style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "3px",
                      background: "rgba(56, 189, 248, 0.15)",
                      color: "#38bdf8",
                      borderRadius: "4px",
                      padding: "1px 5px",
                      fontSize: "10px",
                      fontWeight: 600
                    }}>
                      <Clock size={10} />
                      {tsLabel}
                    </span>
                  )}
                  {src.topic && (
                    <span className="source-topic-pill" style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "3px",
                      background: "rgba(168, 85, 247, 0.15)",
                      color: "#c084fc",
                      borderRadius: "4px",
                      padding: "1px 5px",
                      fontSize: "10px",
                      fontWeight: 500
                    }}>
                      <Tag size={9} />
                      {src.topic}
                    </span>
                  )}
                </div>
                <div className="source-text">{src.chunk_text}</div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
