import React, { useState } from "react";
import { ChevronDown, FileText } from "lucide-react";

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
          {sources.map((src, i) => (
            <div key={i} className="source-item">
              <div className="source-name">
                <FileText size={11} />
                {src.document_name}
              </div>
              <div className="source-text">{src.chunk_text}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
