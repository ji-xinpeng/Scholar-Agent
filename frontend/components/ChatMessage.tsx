"use client";

import { User, Bot, FileText } from "lucide-react";

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
}

export default function ChatMessage({ role, content, image, attachments, isStreaming }: ChatMessageProps) {
  const isUser = role === "user";

  const renderMarkdown = (text: string) => {
    let html = text;
    
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    
    const lines = html.split("\n");
    const result = [];
    
    for (const line of lines) {
      if (line.startsWith("### ")) {
        result.push(`<h4 class='text-sm font-semibold mt-3 mb-1'>${line.slice(4)}</h4>`);
      } else if (line.startsWith("## ")) {
        result.push(`<h3 class='text-base font-semibold mt-4 mb-2'>${line.slice(3)}</h3>`);
      } else if (line.startsWith("# ")) {
        result.push(`<h2 class='text-lg font-semibold mt-4 mb-2'>${line.slice(2)}</h2>`);
      } else if (line.startsWith("- ")) {
        result.push(`<li class='ml-4 list-disc'>${line.slice(2)}</li>`);
      } else if (line.trim() === "") {
        result.push("<br/>");
      } else {
        result.push(line);
      }
    }
    
    return result.join("");
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  };

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
          isUser ? "bg-indigo-500" : "bg-gradient-to-br from-purple-500 to-indigo-600"
        }`}
      >
        {isUser ? <User className="w-4 h-4 text-white" /> : <Bot className="w-4 h-4 text-white" />}
      </div>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
          isUser
            ? "bg-indigo-500 text-white rounded-tr-sm"
            : "bg-white border border-gray-200 text-gray-800 rounded-tl-sm shadow-sm"
        }`}
      >
        {image && (
          <img src={image} alt="用户上传的图片" className="max-w-[240px] rounded-lg mb-2" />
        )}
        {attachments && attachments.length > 0 && (
          <div className="mb-2 space-y-1">
            {attachments.map((attachment) => (
              <div
                key={attachment.id}
                className={`flex items-center gap-2 p-2 rounded-lg ${isUser ? "bg-indigo-600/50" : "bg-gray-100"}`}
              >
                {attachment.preview ? (
                  <img src={attachment.preview} alt="" className="w-8 h-8 rounded object-cover" />
                ) : (
                  <FileText className={`w-5 h-5 ${isUser ? "text-indigo-200" : "text-gray-500"}`} />
                )}
                <div className="flex-1 min-w-0">
                  <span className={`text-xs font-medium truncate ${isUser ? "text-white" : "text-gray-700"}`}>
                    {attachment.file.name}
                  </span>
                  <span className={`text-[10px] ${isUser ? "text-indigo-200" : "text-gray-400"}`}>
                    {formatFileSize(attachment.file.size)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
        {content && content !== "[图片]" ? (
          <div className="break-words prose prose-sm max-w-none" dangerouslySetInnerHTML={{
            __html: renderMarkdown(content)
          }} />
        ) : !image && (!attachments || attachments.length === 0) && isStreaming ? (
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
          </div>
        ) : null}
      </div>
    </div>
  );
}
