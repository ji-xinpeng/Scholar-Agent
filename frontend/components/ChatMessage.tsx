"use client";

import { User, Bot } from "lucide-react";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  image?: string;
  isStreaming?: boolean;
}

export default function ChatMessage({ role, content, image, isStreaming }: ChatMessageProps) {
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
        {content && content !== "[图片]" ? (
          <div className="break-words prose prose-sm max-w-none" dangerouslySetInnerHTML={{
            __html: renderMarkdown(content)
          }} />
        ) : !image && isStreaming ? (
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
