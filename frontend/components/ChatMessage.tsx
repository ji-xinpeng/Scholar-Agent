"use client";

import { User, Bot, FileText, ExternalLink } from "lucide-react";

interface FileAttachment {
  id: string;
  file: File;
  preview?: string;
  uploading?: boolean;
  uploaded?: boolean;
  docId?: string;
}

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  image?: string;
  attachments?: FileAttachment[];
  isStreaming?: boolean;
  onDocRefClick?: (docId: string) => void;
}

export default function ChatMessage({ role, content, image, attachments, isStreaming, onDocRefClick }: ChatMessageProps) {
  const isUser = role === "user";

  const handleDocRefClick = (e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    const docRef = target.closest('[data-doc-id]');
    if (docRef && onDocRefClick) {
      e.preventDefault();
      const docId = docRef.getAttribute('data-doc-id');
      if (docId) {
        onDocRefClick(docId);
      }
    }
  };

  const renderMarkdown = (text: string) => {
    let html = text;

    html = html.replace(/\[文档引用: ([^\]]+)\]\(([^)]+)\)/g, (_m, docName, docId) => {
      return `<span class="doc-ref inline-flex items-center gap-1 px-2.5 py-1 bg-violet-50 text-violet-700 rounded-lg text-xs font-medium cursor-pointer hover:bg-violet-100 transition-colors border border-violet-200/60 shadow-sm" data-doc-id="${docId}"><ExternalLink class="w-3 h-3" />${docName}</span>`;
    });

    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (_m, lang, code) => {
      return `<div class="my-3 rounded-xl overflow-hidden border border-slate-200/80 shadow-sm"><div class="bg-slate-100/90 px-3 py-1.5 text-[10px] font-mono text-slate-500 border-b border-slate-200/80">${lang || "code"}</div><pre class="bg-slate-800/95 text-slate-100 text-xs p-4 overflow-x-auto leading-relaxed"><code>${code.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</code></pre></div>`;
    });

    html = html.replace(/`([^`]+)`/g, '<code class="px-2 py-0.5 bg-slate-100 text-slate-700 rounded-md text-xs font-mono border border-slate-200/80">$1</code>');

    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\*(.*?)\*/g, "<em>$1</em>");

    const lines = html.split("\n");
    const result: string[] = [];
    let inList = false;

    for (const line of lines) {
      if (line.startsWith("### ")) {
        if (inList) { result.push("</ul>"); inList = false; }
        result.push(`<h4 class='text-sm font-semibold text-slate-800 mt-4 mb-1.5'>${line.slice(4)}</h4>`);
      } else if (line.startsWith("## ")) {
        if (inList) { result.push("</ul>"); inList = false; }
        result.push(`<h3 class='text-[15px] font-semibold text-slate-800 mt-5 mb-2'>${line.slice(3)}</h3>`);
      } else if (line.startsWith("# ")) {
        if (inList) { result.push("</ul>"); inList = false; }
        result.push(`<h2 class='text-base font-bold text-slate-900 mt-5 mb-2'>${line.slice(2)}</h2>`);
      } else if (line.match(/^\d+\.\s/)) {
        if (inList) { result.push("</ul>"); inList = false; }
        const content = line.replace(/^\d+\.\s/, "");
        result.push(`<div class='flex gap-2 my-0.5'><span class='text-indigo-400 font-semibold shrink-0'>${line.match(/^\d+/)![0]}.</span><span>${content}</span></div>`);
      } else if (line.startsWith("- ")) {
        if (!inList) { result.push("<ul class='space-y-0.5 my-1'>"); inList = true; }
        result.push(`<li class='flex gap-2 items-start'><span class='text-indigo-400 mt-[7px] shrink-0'>•</span><span>${line.slice(2)}</span></li>`);
      } else if (line.trim() === "") {
        if (inList) { result.push("</ul>"); inList = false; }
        result.push("<div class='h-2'></div>");
      } else {
        if (inList) { result.push("</ul>"); inList = false; }
        result.push(`<p class='my-0.5'>${line}</p>`);
      }
    }
    if (inList) result.push("</ul>");

    return result.join("");
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  return (
    <div className={`flex gap-3 animate-fade-in ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* Avatar */}
      <div
        className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ring-2 ring-white/80 shadow-md ${
          isUser
            ? "bg-gradient-to-br from-indigo-500 to-violet-600"
            : "bg-gradient-to-br from-violet-500 to-fuchsia-500"
        }`}
      >
        {isUser ? <User className="w-4 h-4 text-white" strokeWidth={2.2} /> : <Bot className="w-4 h-4 text-white" strokeWidth={2.2} />}
      </div>

      {/* Message Bubble */}
      <div
        className={`max-w-[82%] text-sm leading-relaxed ${
          isUser
            ? "bg-gradient-to-br from-indigo-500 to-violet-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 shadow-md shadow-indigo-200/40"
            : "text-slate-700 bg-white/90 rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm border border-slate-100/80"
        }`}
      >
        {/* Image */}
        {image && (
          <img
            src={image}
            alt="用户上传的图片"
            className="max-w-[280px] rounded-xl mb-2 shadow-md border border-white/20"
          />
        )}

        {/* Attachments */}
        {attachments && attachments.length > 0 && (
          <div className="mb-2 space-y-1.5">
            {attachments.map((attachment) => (
              <div
                key={attachment.id}
                className={`flex items-center gap-2.5 p-2.5 rounded-xl ${
                  isUser ? "bg-white/20" : "bg-slate-50/80 border border-slate-200/80"
                }`}
              >
                {attachment.preview ? (
                  <img src={attachment.preview} alt="" className="w-8 h-8 rounded object-cover" />
                ) : (
                  <div className={`w-8 h-8 rounded flex items-center justify-center ${isUser ? "bg-white/10" : "bg-slate-100"}`}>
                    <FileText className={`w-4 h-4 ${isUser ? "text-indigo-200" : "text-slate-400"}`} />
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <div className={`text-xs font-medium truncate ${isUser ? "text-white" : "text-slate-700"}`}>
                    {attachment.file.name}
                  </div>
                  <div className={`text-[10px] ${isUser ? "text-indigo-200" : "text-slate-400"}`}>
                    {formatFileSize(attachment.file.size)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Content */}
        {content && content !== "[图片]" ? (
          <div
            className={`break-words ${isUser ? "" : "prose-agent"}`}
            onClick={handleDocRefClick}
            dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
          />
        ) : !image && (!attachments || attachments.length === 0) && isStreaming ? (
          <div className="flex items-center gap-1.5 py-1">
            <div className="flex gap-1">
              <div className="w-2 h-2 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
              <div className="w-2 h-2 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: "120ms" }} />
              <div className="w-2 h-2 bg-violet-400 rounded-full animate-bounce" style={{ animationDelay: "240ms" }} />
            </div>
          </div>
        ) : null}

        {/* Streaming cursor */}
        {isStreaming && content && (
          <span className="inline-block w-0.5 h-4 bg-violet-500 rounded-full animate-blink ml-0.5 align-middle" />
        )}
      </div>
    </div>
  );
}
