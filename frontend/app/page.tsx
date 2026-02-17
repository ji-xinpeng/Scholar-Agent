"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Send, Globe, Zap, ImagePlus, Sparkles, AlertCircle } from "lucide-react";
import Sidebar from "@/components/Sidebar";
import ChatMessage from "@/components/ChatMessage";
import TaskProgress, { TaskStep } from "@/components/TaskProgress";
import { fetchSSEChat, getMessages, getUsageStats } from "@/lib/api";

interface Msg {
  id?: string;
  role: "user" | "assistant";
  content: string;
  image?: string; // base64 图片预览
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [mode, setMode] = useState<"normal" | "agent">("normal");
  const [webSearch, setWebSearch] = useState(false);
  const [taskSteps, setTaskSteps] = useState<TaskStep[]>([]);
  const [showTaskSteps, setShowTaskSteps] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [lastCost, setLastCost] = useState<{cost: number; balance: number} | null>(null);
  const [costError, setCostError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = useCallback(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent, taskSteps, showTaskSteps, scrollToBottom]);

  const loadSession = async (id: string) => {
    setSessionId(id);
    setTaskSteps([]);
    setShowTaskSteps(false);
    setStreamingContent("");
    try {
      const data = await getMessages(id);
      setMessages((data.messages || []).map((m: any) => ({ id: m.id, role: m.role, content: m.content })));
    } catch {
      setMessages([]);
    }
  };

  const handleNewChat = () => {
    setSessionId(null);
    setMessages([]);
    setTaskSteps([]);
    setShowTaskSteps(false);
    setStreamingContent("");
    inputRef.current?.focus();
  };

  const handleImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) return;
    setImageFile(file);
    const reader = new FileReader();
    reader.onload = (ev) => {
      setImagePreview(ev.target?.result as string);
    };
    reader.readAsDataURL(file);
    // 清空 input 以便可以重复选同一张图
    e.target.value = "";
  };

  const removeImage = () => {
    setImagePreview(null);
    setImageFile(null);
  };

  const handleSubmit = async () => {
    const text = input.trim();
    if (!text && !imagePreview) return;
    if (isLoading) return;

    const userMsg: Msg = { role: "user", content: text || "[图片]", image: imagePreview || undefined };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setImagePreview(null);
    setImageFile(null);
    setIsLoading(true);
    setStreamingContent("");
    setTaskSteps([]);
    setShowTaskSteps(false);
    setCostError(null);
    setLastCost(null);

    let accumulated = "";

    try {
      const returnedId = await fetchSSEChat(
        text,
        sessionId,
        mode,
        webSearch,
        (event) => {
          const { type, data } = event;

          switch (type) {
            case "plan":
              setTaskSteps(
                (data.plan || []).map((s: any) => ({
                  id: s.id,
                  action: s.action,
                  status: "pending" as const,
                }))
              );
              setShowTaskSteps(true);
              break;

            case "step_start":
              setTaskSteps((prev) =>
                prev.map((s) =>
                  s.id === data.step_id ? { ...s, status: "running" as const, message: "" } : s
                )
              );
              break;

            case "step_progress":
              setTaskSteps((prev) =>
                prev.map((s) =>
                  s.id === data.step_id
                    ? { ...s, progress: data.progress, message: data.message }
                    : s
                )
              );
              break;

            case "step_complete":
              setTaskSteps((prev) =>
                prev.map((s) =>
                  s.id === data.step_id ? { ...s, status: "done" as const, progress: 1 } : s
                )
              );
              break;

            case "stream":
              accumulated += data.content || "";
              setStreamingContent(accumulated);
              break;

            case "cost":
              setLastCost({ cost: data.cost, balance: data.balance });
              break;

            case "done":
              break;
          }
        },
        () => {
          if (accumulated) {
            setMessages((prev) => [...prev, { role: "assistant", content: accumulated }]);
          }
          setStreamingContent("");
          setIsLoading(false);
        }
      );

      if (returnedId && !sessionId) {
        setSessionId(returnedId);
      }
    } catch (err: any) {
      setIsLoading(false);
      // 处理 402 余额不足错误
      if (err?.status === 402 || err?.message?.includes("402")) {
        setCostError(err?.detail?.message || "额度不足，请充值后重试。");
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex flex-1 overflow-hidden">
      <Sidebar
        currentSessionId={sessionId}
        onSelectSession={loadSession}
        onNewChat={handleNewChat}
      />

      <div className="flex-1 flex flex-col min-w-0">
        {/* 消息区域 */}
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 && !isLoading ? (
            <div className="flex flex-col items-center justify-center h-full text-center px-4">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mb-4">
                <Sparkles className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-xl font-semibold text-gray-800 mb-2">Scholar Agent</h2>
              <p className="text-gray-500 text-sm max-w-md">
                AI驱动的智能学术研究助手。你可以提问、搜索论文，或切换到智能体模式获取完整的文献综述。
              </p>
              <div className="grid grid-cols-2 gap-3 mt-6 max-w-lg">
                {[
                  "大语言模型推理能力的最新进展有哪些？",
                  "解释一下 Transformer 架构",
                  "比较 RAG 和微调方法的优劣",
                  "总结多模态 AI 的最新研究工作",
                ].map((q) => (
                  <button
                    key={q}
                    onClick={() => { setInput(q); inputRef.current?.focus(); }}
                    className="text-left text-sm p-3 rounded-xl border border-gray-200 hover:border-indigo-300 hover:bg-indigo-50 transition-colors text-gray-600"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto p-6 space-y-5">
              {messages.map((msg, i) => {
                const isLastMessage = i === messages.length - 1;
                const isLastAssistantMessage = isLastMessage && msg.role === "assistant";
                const isStreamingActive = !!streamingContent;
                
                return (
                  <>
                    {!isStreamingActive && isLastAssistantMessage && showTaskSteps && taskSteps.length > 0 && (
                      <div className="flex gap-3" key="task-steps">
                        <div className="w-8" />
                        <TaskProgress steps={taskSteps} />
                      </div>
                    )}
                    <ChatMessage key={i} role={msg.role} content={msg.content} image={msg.image} />
                    {!isStreamingActive && !isLastAssistantMessage && isLastMessage && showTaskSteps && taskSteps.length > 0 && (
                      <div className="flex gap-3" key="task-steps-end">
                        <div className="w-8" />
                        <TaskProgress steps={taskSteps} />
                      </div>
                    )}
                  </>
                );
              })}
              {!messages.length && !streamingContent && showTaskSteps && taskSteps.length > 0 && (
                <div className="flex gap-3">
                  <div className="w-8" />
                  <TaskProgress steps={taskSteps} />
                </div>
              )}
              {streamingContent && (
                <>
                  {showTaskSteps && taskSteps.length > 0 && (
                    <div className="flex gap-3">
                      <div className="w-8" />
                      <TaskProgress steps={taskSteps} />
                    </div>
                  )}
                  <ChatMessage role="assistant" content={streamingContent} isStreaming />
                </>
              )}
              {isLoading && !streamingContent && taskSteps.length === 0 && (
                <ChatMessage role="assistant" content="" isStreaming />
              )}
              {lastCost && lastCost.cost > 0 && (
                <div className="flex justify-center">
                  <span className="text-xs text-gray-400 bg-gray-100 px-3 py-1 rounded-full">
                    本次消耗 ¥{lastCost.cost.toFixed(2)} · 余额 ¥{lastCost.balance.toFixed(2)}
                  </span>
                </div>
              )}
              {lastCost && lastCost.cost === 0 && messages.length > 0 && (
                <div className="flex justify-center">
                  <span className="text-xs text-gray-400 bg-gray-100 px-3 py-1 rounded-full">
                    免费额度 · 余额 ¥{lastCost.balance.toFixed(2)}
                  </span>
                </div>
              )}
              <div ref={endRef} />
            </div>
          )}
        </div>

        {/* 输入区域 */}
        <div className="border-t border-gray-200 bg-white p-4">
          <div className="max-w-3xl mx-auto">
            {/* 余额不足提示 */}
            {costError && (
              <div className="mb-3 flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span className="flex-1">{costError}</span>
                <a href="/profile" className="text-red-600 underline font-medium shrink-0">去充值</a>
                <button onClick={() => setCostError(null)} className="text-red-400 hover:text-red-600 ml-1">×</button>
              </div>
            )}
            {/* 模式与功能开关 */}
            <div className="flex items-center gap-2 mb-3">
              <button
                onClick={() => setMode(mode === "normal" ? "agent" : "normal")}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  mode === "agent"
                    ? "bg-indigo-100 text-indigo-700 ring-1 ring-indigo-300"
                    : "bg-gray-100 text-gray-500 hover:bg-gray-200"
                }`}
              >
                <Zap className="w-3.5 h-3.5" />
                {mode === "agent" ? "智能体模式" : "普通模式"}
              </button>
              <button
                onClick={() => setWebSearch(!webSearch)}
                className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  webSearch
                    ? "bg-emerald-100 text-emerald-700 ring-1 ring-emerald-300"
                    : "bg-gray-100 text-gray-500 hover:bg-gray-200"
                }`}
              >
                <Globe className="w-3.5 h-3.5" />
                联网搜索
              </button>
            </div>

            {/* 图片预览 */}
            {imagePreview && (
              <div className="mb-2 relative inline-block">
                <img src={imagePreview} alt="预览" className="h-20 rounded-lg border border-gray-200 object-cover" />
                <button
                  onClick={removeImage}
                  className="absolute -top-2 -right-2 w-5 h-5 bg-red-500 text-white rounded-full flex items-center justify-center text-xs hover:bg-red-600"
                >
                  ×
                </button>
              </div>
            )}

            {/* 文本输入 */}
            <div className="flex items-end gap-2 bg-gray-50 border border-gray-200 rounded-2xl p-2 focus-within:border-indigo-300 focus-within:ring-2 focus-within:ring-indigo-100 transition-all">
              <input
                ref={imageInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleImageSelect}
              />
              <button
                onClick={() => imageInputRef.current?.click()}
                className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-200 shrink-0"
                title="上传图片"
              >
                <ImagePlus className="w-5 h-5" />
              </button>
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={1}
                placeholder={mode === "agent" ? "描述你的研究任务..." : "输入你的问题..."}
                className="flex-1 resize-none bg-transparent outline-none text-sm text-gray-800 placeholder-gray-400 max-h-32 py-2"
                style={{ minHeight: "36px" }}
              />
              <button
                onClick={handleSubmit}
                disabled={(!input.trim() && !imagePreview) || isLoading}
                className="p-2 bg-indigo-500 text-white rounded-xl hover:bg-indigo-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors shrink-0"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
