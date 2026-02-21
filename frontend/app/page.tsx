"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { 
  Send, Globe, ImagePlus, Sparkles, AlertCircle,
  Upload, FolderPlus, Trash2, FileText, File, FolderOpen,
  ChevronLeft, ChevronRight, Search, Folder, Paperclip,
  X, Save, MessageCircle, Bot, Quote
} from "lucide-react";
import Sidebar from "@/components/Sidebar";
import ChatMessage from "@/components/ChatMessage";
import TaskProgress, { TaskStep, AgentTimelineEvent } from "@/components/TaskProgress";
import { 
  fetchSSEChat, getMessages, 
  uploadDocument, getDocuments, deleteDocument,
  createFolder, getFolders, deleteFolder,
  getDocumentContent, updateDocumentContent
} from "@/lib/api";
import { formatFileSize, formatDate } from "@/lib/utils";

interface Msg {
  id?: string;
  role: "user" | "assistant";
  content: string;
  image?: string;
  attachments?: any[];
  metadata?: {
    task_plan?: TaskStep[];
    agent_thought?: string;
    step_thoughts?: Record<string, string>;
    timeline?: AgentTimelineEvent[];
  };
}

interface Attachment {
  id: string;
  file: File;
  preview?: string;
  uploading: boolean;
  docId?: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [deepResearch, setDeepResearch] = useState(false);
  const [taskSteps, setTaskSteps] = useState<TaskStep[]>([]);
  const [agentThought, setAgentThought] = useState<string>("");
  const [stepThoughts, setStepThoughts] = useState<Record<string, string>>({});
  const [showTaskSteps, setShowTaskSteps] = useState(false);
  const [agentTimeline, setAgentTimeline] = useState<AgentTimelineEvent[]>([]);
  const [agentContinuingMessage, setAgentContinuingMessage] = useState<string>("");
  const [streamingContent, setStreamingContent] = useState("");
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [lastCost, setLastCost] = useState<{cost: number; balance: number} | null>(null);
  const [costError, setCostError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [abortController, setAbortController] = useState<AbortController | null>(null);

  const [documents, setDocuments] = useState<any[]>([]);
  const [folders, setFolders] = useState<any[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const [docPage, setDocPage] = useState(1);
  const [docTotal, setDocTotal] = useState(0);
  const [docPageSize] = useState(10);
  const [docUploading, setDocUploading] = useState(false);
  const [showNewFolder, setShowNewFolder] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");
  const [docSearchQuery, setDocSearchQuery] = useState("");

  const [selectedDoc, setSelectedDoc] = useState<any>(null);
  const [docContent, setDocContent] = useState<string | null>(null);
  const [docEditingContent, setDocEditingContent] = useState<string>("");
  const [docContentDirty, setDocContentDirty] = useState(false);
  const [docSaving, setDocSaving] = useState(false);
  const [docLoading, setDocLoading] = useState(false);

  const [paperPanelWidth, setPaperPanelWidth] = useState(288);
  const [docPanelWidth, setDocPanelWidth] = useState(320);
  const resizeStartRef = useRef<{ type: "paper" | "doc"; startX: number; startW: number } | null>(null);
  
  const [selectedText, setSelectedText] = useState<string>("");
  const [selectionMenuPosition, setSelectionMenuPosition] = useState<{ x: number; y: number } | null>(null);
  const docContentRef = useRef<HTMLDivElement>(null);

  const taskStateRef = useRef({ taskSteps, agentThought, stepThoughts, showTaskSteps, agentTimeline });
  taskStateRef.current = { taskSteps, agentThought, stepThoughts, showTaskSteps, agentTimeline };

  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const docFileInputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = useCallback(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  const handleTextSelection = useCallback((e?: any) => {
    setTimeout(() => {
      const selection = window.getSelection();
      if (!selection || selection.rangeCount === 0) {
        setSelectionMenuPosition(null);
        setSelectedText("");
        return;
      }

      const range = selection.getRangeAt(0);
      const text = selection.toString().trim();

      if (!text) {
        setSelectionMenuPosition(null);
        setSelectedText("");
        return;
      }

      if (docContentRef.current && docContentRef.current.contains(range.commonAncestorContainer)) {
        const rect = range.getBoundingClientRect();
        setSelectedText(text);
        setSelectionMenuPosition({
          x: rect.left + rect.width / 2,
          y: rect.top - 10
        });
      } else {
        setSelectionMenuPosition(null);
        setSelectedText("");
      }
    }, 10);
  }, []);

  const addToChat = useCallback(() => {
    if (!selectedText || !selectedDoc) return;
    const quotedText = `> ${selectedText.replace(/\n/g, "\n> ")}`;
    const docMarker = `[文档引用: ${selectedDoc.original_name}](${selectedDoc.id})`;
    setInput((prev) => prev + (prev ? "\n\n" : "") + `${quotedText}\n\n${docMarker}`);
    
    if (!selectedDocumentIds.includes(selectedDoc.id)) {
      setSelectedDocumentIds((prev) => [...prev, selectedDoc.id]);
    }
    
    setSelectionMenuPosition(null);
    setSelectedText("");
    window.getSelection()?.removeAllRanges();
    inputRef.current?.focus();
  }, [selectedText, selectedDoc, selectedDocumentIds]);

  const clearSelection = useCallback(() => {
    setSelectionMenuPosition(null);
    setSelectedText("");
  }, []);

  const handleDocRefClick = useCallback((docId: string) => {
    const doc = documents.find((d) => d.id === docId);
    if (doc) {
      handleDocumentClick(doc);
    }
  }, [documents]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingContent, taskSteps, showTaskSteps, scrollToBottom]);

  useEffect(() => {
    document.addEventListener("mousedown", (e) => {
      if (selectionMenuPosition) {
        const target = e.target as HTMLElement;
        if (!target.closest(".selection-menu")) {
          clearSelection();
        }
      }
    });
  }, [selectionMenuPosition, clearSelection]);

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      const r = resizeStartRef.current;
      if (!r) return;
      const delta = e.clientX - r.startX;
      if (r.type === "paper") {
        setPaperPanelWidth((w) => Math.min(480, Math.max(200, w + delta)));
      } else {
        setDocPanelWidth((w) => Math.min(560, Math.max(240, w + delta)));
      }
      r.startX = e.clientX;
    };
    const onMouseUp = () => {
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      resizeStartRef.current = null;
    };
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
    return () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    };
  }, []);

  const startResize = (type: "paper" | "doc", startX: number) => {
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    resizeStartRef.current = { type, startX, startW: type === "paper" ? paperPanelWidth : docPanelWidth };
  };

  const loadDocuments = async () => {
    try {
      const [docsRes, foldersRes] = await Promise.all([
        getDocuments(docPage, docPageSize, selectedFolder || undefined),
        getFolders(),
      ]);
      setDocuments(docsRes.documents || []);
      setDocTotal(docsRes.total || 0);
      setFolders(foldersRes.folders || []);
    } catch {}
  };

  useEffect(() => { loadDocuments(); }, [docPage, selectedFolder]);

  const loadSession = async (id: string) => {
    setSessionId(id);
    setTaskSteps([]);
    setAgentThought("");
    setStepThoughts({});
    setShowTaskSteps(false);
    setStreamingContent("");
    setAgentTimeline([]);
    try {
      const data = await getMessages(id);
      const loadedMessages = (data.messages || []).map((m: any) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        metadata: m.metadata ? {
          task_plan: m.metadata.task_plan,
          agent_thought: m.metadata.agent_thought,
          step_thoughts: m.metadata.step_thoughts,
          timeline: m.metadata.timeline,
        } : undefined,
      }));
      setMessages(loadedMessages);
      
      const lastAssistantMsg = [...loadedMessages].reverse().find((m: Msg) => m.role === "assistant" && m.metadata);
      if (lastAssistantMsg?.metadata) {
        if (lastAssistantMsg.metadata.task_plan?.length > 0) {
          setTaskSteps(lastAssistantMsg.metadata.task_plan);
          setAgentThought(lastAssistantMsg.metadata.agent_thought || "");
          setStepThoughts(lastAssistantMsg.metadata.step_thoughts || {});
          setAgentTimeline(lastAssistantMsg.metadata.timeline || []);
          setShowTaskSteps(true);
        }
      }
    } catch {
      setMessages([]);
    }
  };

  const handleNewChat = () => {
    setSessionId(null);
    setMessages([]);
    setTaskSteps([]);
    setAgentThought("");
    setStepThoughts({});
    setShowTaskSteps(false);
    setStreamingContent("");
    setAttachments([]);
    setSelectedDocumentIds([]);
    setAgentTimeline([]);
    setDeepResearch(false);
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
    e.target.value = "";
  };

  const removeImage = () => {
    setImagePreview(null);
    setImageFile(null);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    for (const file of Array.from(files)) {
      const id = Date.now() + Math.random().toString(36).substr(2, 9);
      const newAttachment: Attachment = { id, file, uploading: true };
      
      if (file.type.startsWith("image/")) {
        const reader = new FileReader();
        reader.onload = (ev) => {
          newAttachment.preview = ev.target?.result as string;
          setAttachments((prev) => [...prev, newAttachment]);
        };
        reader.readAsDataURL(file);
      } else {
        setAttachments((prev) => [...prev, newAttachment]);
      }

      uploadDocument(file)
        .then((res) => {
          setAttachments((prev) => prev.map(a =>
            a.id === id ? { ...a, uploading: false, docId: res.id } : a
          ));
          setSelectedDocumentIds((prev) => [...prev, res.id]);
        })
        .catch(() => {
          setAttachments((prev) => prev.filter(a => a.id !== id));
          setCostError("文件上传失败，请检查网络或重试");
        });
    }
    e.target.value = "";
  };

  const removeAttachment = (id: string) => {
    const att = attachments.find(a => a.id === id);
    if (att?.docId) {
      setSelectedDocumentIds((prev) => prev.filter(i => i !== att.docId!));
    }
    setAttachments((prev) => prev.filter(a => a.id !== id));
  };

  const handleDocumentClick = async (doc: any) => {
    setSelectedDoc(doc);
    setDocContentDirty(false);
    setDocLoading(true);
    try {
      const res = await getDocumentContent(doc.id);
      const content = res.content ?? "";
      setDocContent(content);
      setDocEditingContent(content);
    } catch {
      setDocContent(null);
      setDocEditingContent("");
    } finally {
      setDocLoading(false);
    }
  };

  const isDocEditable = (doc: any) =>
    doc && ["word", "markdown", "text"].includes(doc.file_type);

  const handleSaveDocContent = async () => {
    if (!selectedDoc || !docContentDirty) return;
    setDocSaving(true);
    try {
      await updateDocumentContent(selectedDoc.id, docEditingContent);
      setDocContent(docEditingContent);
      setDocContentDirty(false);
      setCostError(null);
    } catch (e: any) {
      setCostError(e?.message || "保存失败");
    } finally {
      setDocSaving(false);
    }
  };

  const handleDocUpload = async (files: FileList | null) => {
    if (!files) return;
    setDocUploading(true);
    for (const file of Array.from(files)) {
      await uploadDocument(file, selectedFolder || undefined);
    }
    setDocUploading(false);
    loadDocuments();
  };

  const handleDocDrop = (e: React.DragEvent) => {
    e.preventDefault();
    handleDocUpload(e.dataTransfer.files);
  };

  const handleDeleteDoc = async (docId: string) => {
    await deleteDocument(docId);
    if (selectedDoc?.id === docId) {
      setSelectedDoc(null);
      setDocContent(null);
    }
    loadDocuments();
  };

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return;
    await createFolder(newFolderName.trim());
    setNewFolderName("");
    setShowNewFolder(false);
    loadDocuments();
  };

  const handleDeleteFolder = async (folderId: string) => {
    await deleteFolder(folderId);
    if (selectedFolder === folderId) setSelectedFolder(null);
    loadDocuments();
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleChatDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    try {
      const docData = e.dataTransfer.getData("application/json");
      if (docData) {
        const doc = JSON.parse(docData);
        setSelectedDocumentIds((prev) => [...prev, doc.id]);
        setInput((prev) => prev + (prev ? "\n" : "") + `[文档: ${doc.original_name}]`);
      }
    } catch {}
  };

  const handleSubmit = async () => {
    const text = input.trim();
    if (!text && !imagePreview && attachments.length === 0) return;
    if (isLoading) return;

    const imageToSend = imagePreview || null;
    const userMsg: Msg = { 
      role: "user", 
      content: text || "[图片]", 
      image: imagePreview || undefined,
      attachments: attachments.length > 0 ? attachments : undefined
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setImagePreview(null);
    setImageFile(null);
    setAttachments([]);
    setIsLoading(true);
    setStreamingContent("");
    setCostError(null);
    setLastCost(null);

    setTaskSteps([]);
    setAgentThought("");
    setStepThoughts({});
    setAgentTimeline([]);
    setShowTaskSteps(true);

    const controller = new AbortController();
    setAbortController(controller);
    let accumulated = "";

    try {
      const returnedId = await fetchSSEChat(
        text,
        sessionId,
        deepResearch,
        (event) => {
          const { type, data } = event;

          switch (type) {
            case "thinking":
              if (data.message) {
                setAgentThought(data.message);
                setAgentTimeline((prev) => {
                  const last = prev[prev.length - 1];
                  if (last?.type === "thought" && last.content === data.message) {
                    return prev;
                  }
                  return [...prev, { type: "thought", content: data.message }];
                });
              }
              break;

            case "plan":
              setTaskSteps((prev) => {
                const prevMap = new Map(prev.map((s) => [s.id, s]));
                return (data.plan || []).map((s: any) => {
                  const existing = prevMap.get(s.id);
                  const backendStatus = s.status === "done" ? "done" as const : s.status === "running" ? "running" as const : "pending" as const;
                  if (existing) {
                    const finalStatus = existing.status === "done" ? "done" as const : backendStatus !== "pending" ? backendStatus : existing.status;
                    return {
                      ...existing,
                      action: s.action || existing.action,
                      tool_name: s.tool_name || existing.tool_name,
                      params: s.params || existing.params,
                      status: finalStatus,
                    };
                  }
                  return {
                    id: s.id,
                    action: s.action,
                    status: backendStatus,
                    tool_name: s.tool_name,
                    params: s.params,
                  };
                });
              });
              if (data.thought) setAgentThought(data.thought);
              setShowTaskSteps(true);
              break;

            case "step_start":
              setAgentContinuingMessage("");
              setTaskSteps((prev) =>
                prev.map((s) =>
                  s.id === data.step_id ? { ...s, status: "running" as const, message: "", tool_name: data.tool_name, params: data.params } : s
                )
              );
              setAgentTimeline((prev) => [...prev, { type: "step_start", stepId: data.step_id, toolName: data.tool_name, action: data.action || "" }]);
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
                  s.id === data.step_id ? { 
                    ...s, 
                    status: "done" as const, 
                    progress: 1,
                    tool_name: data.tool_name,
                    params: data.params,
                    result: data.result
                  } : s
                )
              );
              if (data.step_id && data.thought_summary) {
                setStepThoughts((prev) => ({ ...prev, [data.step_id]: data.thought_summary }));
              }
              setAgentTimeline((prev) => [...prev, { type: "step_done", stepId: data.step_id, result: data.thought_summary || "" }]);
              
              // 强制滚动到底部，确保最新步骤可见
              setTimeout(() => {
                 const element = document.getElementById(`step-${data.step_id}`);
                 element?.scrollIntoView({ behavior: "smooth", block: "nearest" });
              }, 100);
              break;

            case "agent_continuing":
              setAgentContinuingMessage(data.message || "正在准备下一步…");
              break;

            case "stream":
              setAgentContinuingMessage("");
              accumulated += data.content || "";
              setStreamingContent(accumulated);
              break;

            case "cost":
              setLastCost({ cost: data.cost, balance: data.balance });
              break;

            case "doc_updated":
              if (data.doc_id && selectedDoc?.id === data.doc_id) {
                getDocumentContent(data.doc_id).then((res) => {
                  setDocContent(res.content);
                  setDocEditingContent(res.content ?? "");
                  setDocContentDirty(false);
                }).catch(() => {});
              }
              // 刷新整个文档列表
              loadDocuments();
              break;

            case "done":
              setAgentContinuingMessage("");
              break;
          }
        },
        () => {
          if (accumulated) {
            const { taskSteps: ts, agentThought: at, stepThoughts: st, showTaskSteps: ssts, agentTimeline: tl } = taskStateRef.current;
            const taskMeta = ssts && ts.length > 0 ? {
              task_plan: ts.map((s) => ({ 
                id: s.id, 
                action: s.action, 
                status: s.status, 
                progress: s.progress,
                tool_name: s.tool_name,
                params: s.params,
                result: s.result
              })),
              agent_thought: at,
              step_thoughts: st,
              timeline: tl,
            } : undefined;
            setMessages((prev) => [...prev, {
              role: "assistant",
              content: accumulated,
              metadata: taskMeta ? { ...taskMeta } : undefined,
            }]);
          }
          setStreamingContent("");
          setAgentContinuingMessage("");
          setIsLoading(false);
          setAbortController(null);
          setSelectedDocumentIds([]);
        },
        (() => {
          const ids = new Set(selectedDocumentIds);
          if (selectedDoc?.id && !ids.has(selectedDoc.id)) {
            ids.add(selectedDoc.id);
          }
          return ids.size > 0 ? Array.from(ids) : undefined;
        })(),
        controller.signal,
        imageToSend,
      );

      if (returnedId && !sessionId) {
        setSessionId(returnedId);
      }
    } catch (err: any) {
      setIsLoading(false);
      setAbortController(null);
      if (err?.name === "AbortError") {
        if (accumulated) {
          const { taskSteps: ts, agentThought: at, stepThoughts: st, showTaskSteps: ssts, agentTimeline: tl } = taskStateRef.current;
          const taskMeta = ssts && ts.length > 0 ? {
            task_plan: ts.map((s) => ({ 
              id: s.id, 
              action: s.action, 
              status: s.status, 
              progress: s.progress,
              tool_name: s.tool_name,
              params: s.params,
              result: s.result
            })),
            agent_thought: at,
            step_thoughts: st,
            timeline: tl,
          } : undefined;
          setMessages((prev) => [...prev, {
            role: "assistant",
            content: accumulated + "\n\n[已停止]",
            metadata: taskMeta ? { ...taskMeta } : undefined,
          }]);
        }
        setStreamingContent("");
        setSelectedDocumentIds([]);
      } else if (err?.status === 402 || err?.message?.includes("402")) {
        setCostError(err?.detail?.message || "额度不足，请充值后重试。");
      }
    }
  };

  const handleStop = () => {
    if (abortController) {
      abortController.abort();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const totalPages = Math.ceil(docTotal / docPageSize);
  const fileIcon = (type: string) => 
    type === "pdf" ? <FileText className="w-3.5 h-3.5 text-red-400" /> : 
    type === "word" ? <FileText className="w-3.5 h-3.5 text-blue-400" /> : 
    <File className="w-3.5 h-3.5 text-gray-400" />;

  const filteredDocs = docSearchQuery
    ? documents.filter((d) => d.original_name.toLowerCase().includes(docSearchQuery.toLowerCase()))
    : documents;

  return (
    <div className="flex flex-1 overflow-hidden">
      <Sidebar
        currentSessionId={sessionId}
        onSelectSession={loadSession}
        onNewChat={handleNewChat}
      />

      <div
        className="bg-gray-50 border-r border-gray-200 flex flex-col shrink-0"
        style={{ width: paperPanelWidth }}
      >
        <div className="p-3 border-b border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-gray-700">我的论文</span>
            <button 
              onClick={() => setShowNewFolder(true)} 
              className="p-1 hover:bg-gray-200 rounded" 
              title="新建文件夹"
            >
              <FolderPlus className="w-4 h-4 text-gray-500" />
            </button>
          </div>
          {showNewFolder && (
            <div className="flex gap-1 mb-2">
              <input
                autoFocus
                value={newFolderName}
                onChange={(e) => setNewFolderName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreateFolder()}
                placeholder="文件夹名称"
                className="flex-1 text-sm border rounded px-2 py-1 outline-none focus:border-indigo-400"
              />
              <button 
                onClick={handleCreateFolder} 
                className="text-xs px-2 py-1 bg-indigo-500 text-white rounded hover:bg-indigo-600"
              >
                添加
              </button>
            </div>
          )}
        </div>

        <div className="border-b border-gray-200 px-2 py-2">
          <div className="flex items-center gap-2">
            <Search className="w-3.5 h-3.5 text-gray-400" />
            <input
              value={docSearchQuery}
              onChange={(e) => setDocSearchQuery(e.target.value)}
              placeholder="搜索论文..."
              className="flex-1 text-xs bg-transparent outline-none placeholder-gray-400"
            />
          </div>
        </div>

        <div className="px-2 py-1">
          <div
            onClick={() => { setSelectedFolder(null); setDocPage(1); }}
            className={`flex items-center gap-2 p-1.5 rounded-lg cursor-pointer text-xs transition-colors ${
              !selectedFolder ? "bg-indigo-100 text-indigo-700" : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            <FolderOpen className="w-3.5 h-3.5" />
            <span>全部论文</span>
          </div>
          {folders.map((f) => (
            <div
              key={f.id}
              onClick={() => { setSelectedFolder(f.id); setDocPage(1); }}
              className={`group flex items-center gap-2 p-1.5 rounded-lg cursor-pointer text-xs transition-colors ${
                selectedFolder === f.id ? "bg-indigo-100 text-indigo-700" : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              <Folder className="w-3.5 h-3.5" />
              <span className="flex-1 truncate">{f.name}</span>
              <span className="text-[10px] text-gray-400">{f.document_count}</span>
              <button
                onClick={(e) => { e.stopPropagation(); handleDeleteFolder(f.id); }}
                className="p-0.5 rounded opacity-0 group-hover:opacity-100 hover:bg-red-100"
              >
                <Trash2 className="w-3 h-3 text-red-400" />
              </button>
            </div>
          ))}
        </div>

        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDocDrop}
          onClick={() => docFileInputRef.current?.click()}
          className="mx-2 mb-2 border-2 border-dashed border-gray-300 rounded-lg p-3 text-center hover:border-indigo-400 hover:bg-indigo-50 transition-colors cursor-pointer"
        >
          <input 
            ref={docFileInputRef} 
            type="file" 
            multiple 
            accept=".pdf,.doc,.docx,.md,.txt" 
            className="hidden" 
            onChange={(e) => handleDocUpload(e.target.files)} 
          />
          <Upload className={`w-5 h-5 mx-auto mb-1 ${docUploading ? "text-indigo-500 animate-bounce" : "text-gray-400"}`} />
          <p className="text-[11px] text-gray-600 font-medium">
            {docUploading ? "上传中..." : "拖拽或点击上传论文"}
          </p>
        </div>

        <div className="flex-1 overflow-y-auto px-2 pb-2">
          {filteredDocs.length === 0 ? (
            <div className="text-center text-gray-400 text-xs mt-4">暂无论文</div>
          ) : (
            <div className="space-y-1">
              {filteredDocs.map((doc) => (
                <div
                  key={doc.id}
                  onClick={() => handleDocumentClick(doc)}
                  draggable
                  onDragStart={(e) => {
                    e.dataTransfer.setData("application/json", JSON.stringify(doc));
                    e.dataTransfer.setData("text/plain", doc.original_name);
                    e.dataTransfer.effectAllowed = "copy";
                  }}
                  className={`flex items-center gap-2 p-2 rounded-lg hover:shadow-sm hover:border-indigo-300 transition-all cursor-pointer group ${
                    selectedDoc?.id === doc.id 
                      ? "bg-indigo-50 border border-indigo-300" 
                      : "bg-white border border-gray-200"
                  }`}
                >
                  {fileIcon(doc.file_type)}
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium text-gray-800 truncate">{doc.original_name}</div>
                    <div className="text-[10px] text-gray-400">
                      {formatFileSize(doc.file_size)}
                    </div>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDeleteDoc(doc.id); }}
                    className="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-red-50 transition-opacity"
                  >
                    <Trash2 className="w-3.5 h-3.5 text-red-400" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-1 p-2 border-t border-gray-200">
            <button
              onClick={() => setDocPage(Math.max(1, docPage - 1))}
              disabled={docPage === 1}
              className="p-1 rounded hover:bg-gray-200 disabled:opacity-30"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => i + 1).map((p) => (
              <button
                key={p}
                onClick={() => setDocPage(p)}
                className={`w-6 h-6 rounded text-[10px] font-medium transition-colors ${
                  docPage === p ? "bg-indigo-500 text-white" : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                {p}
              </button>
            ))}
            <button
              onClick={() => setDocPage(Math.min(totalPages, docPage + 1))}
              disabled={docPage === totalPages}
              className="p-1 rounded hover:bg-gray-200 disabled:opacity-30"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>

      <div
        className="w-1 shrink-0 bg-gray-200 hover:bg-indigo-400 cursor-col-resize flex items-center justify-center group transition-colors select-none"
        onMouseDown={(e) => { e.preventDefault(); startResize("paper", e.clientX); }}
        title="拖动调节论文面板宽度"
      >
        <div className="w-0.5 h-8 bg-gray-400 group-hover:bg-indigo-500 rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>

      {selectedDoc && (
        <>
        <div
          className="bg-white border-r border-gray-200 flex flex-col shrink-0"
          style={{ width: docPanelWidth }}
        >
          <div className="p-3 border-b border-gray-200 flex items-center justify-between">
            <div className="flex items-center gap-2 min-w-0">
              {fileIcon(selectedDoc.file_type)}
              <span className="text-sm font-semibold text-gray-800 truncate">{selectedDoc.original_name}</span>
            </div>
            <button
              onClick={() => { setSelectedDoc(null); setDocContent(null); setDocEditingContent(""); setDocContentDirty(false); }}
              className="p-1 hover:bg-gray-100 rounded"
            >
              <X className="w-4 h-4 text-gray-500" />
            </button>
          </div>
          <div className="px-3 py-2 border-b border-gray-100 flex items-center justify-between">
            <span className="text-xs text-gray-500">
              {formatFileSize(selectedDoc.file_size)} · {formatDate(selectedDoc.created_at)}
            </span>
            {isDocEditable(selectedDoc) && docContent != null && (
              <button
                onClick={handleSaveDocContent}
                disabled={!docContentDirty || docSaving}
                className="flex items-center gap-1 px-2 py-1 text-xs font-medium text-white bg-indigo-500 rounded hover:bg-indigo-600 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <Save className="w-3 h-3" />
                {docSaving ? "保存中..." : "保存"}
              </button>
            )}
          </div>
          <div className="flex-1 overflow-y-auto p-3 min-h-0 relative" ref={docContentRef}>
            {docLoading ? (
              <div className="flex items-center justify-center h-full">
                <div className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : docContent != null ? (
              isDocEditable(selectedDoc) ? (
                <textarea
                  value={docEditingContent}
                  onChange={(e) => {
                    setDocEditingContent(e.target.value);
                    setDocContentDirty(true);
                  }}
                  onMouseUp={handleTextSelection}
                  onKeyUp={handleTextSelection}
                  className="w-full h-full min-h-[200px] text-xs text-gray-700 font-sans leading-relaxed p-2 border border-gray-200 rounded-lg outline-none focus:border-indigo-400 focus:ring-1 focus:ring-indigo-200 resize-none"
                  placeholder="在此编辑文档内容..."
                  spellCheck={false}
                />
              ) : (
                <pre 
                  className="text-xs text-gray-700 whitespace-pre-wrap font-sans leading-relaxed select-text"
                  onMouseUp={handleTextSelection}
                >
                  {docContent}
                </pre>
              )
            ) : (
              <div className="text-center text-gray-400 text-xs mt-8">
                无法解析或不支持的文件格式
              </div>
            )}
            
            {selectionMenuPosition && (
              <div
                className="selection-menu fixed z-50 bg-white rounded-lg shadow-lg border border-gray-200 py-1 px-2 flex items-center gap-1"
                style={{
                  left: `${selectionMenuPosition.x}px`,
                  top: `${selectionMenuPosition.y}px`,
                  transform: "translateX(-50%) translateY(-100%)"
                }}
              >
                <button
                  onClick={addToChat}
                  className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-indigo-600 hover:bg-indigo-50 rounded-md transition-colors"
                >
                  <Quote className="w-3.5 h-3.5" />
                  添加到对话框中
                </button>
              </div>
            )}
          </div>
        </div>

        <div
          className="w-1 shrink-0 bg-gray-200 hover:bg-indigo-400 cursor-col-resize flex items-center justify-center group transition-colors select-none"
          onMouseDown={(e) => { e.preventDefault(); startResize("doc", e.clientX); }}
          title="拖动调节显示面板宽度"
        >
          <div className="w-0.5 h-8 bg-gray-400 group-hover:bg-indigo-500 rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
        </>
      )}

      <div 
        className="flex-1 flex flex-col min-w-0"
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleChatDrop}
      >
        <div className={`flex-1 overflow-y-auto transition-colors chat-area-bg ${isDragOver ? "bg-violet-50/80" : ""}`}>
          {messages.length === 0 && !isLoading ? (
            <div className="flex flex-col items-center justify-center h-full text-center px-6 min-h-[420px]">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-violet-500 via-fuchsia-500 to-indigo-600 flex items-center justify-center mb-6 shadow-xl shadow-violet-200/50 ring-4 ring-violet-100/50">
                <Sparkles className="w-8 h-8 text-white" strokeWidth={2} />
              </div>
              <h2 className="text-2xl font-bold text-slate-800 mb-2 tracking-tight">Scholar Agent</h2>
              <p className="text-slate-500 text-sm max-w-sm mb-8 leading-relaxed">
                AI 驱动的智能学术研究助手。提问、搜索论文，或从左侧拖拽论文进行分析。
              </p>
              <div className="grid grid-cols-2 gap-3 max-w-xl">
                {[
                  "大语言模型推理能力的最新进展有哪些？",
                  "解释一下 Transformer 架构",
                  "比较 RAG 和微调方法的优劣",
                  "总结多模态 AI 的最新研究工作",
                ].map((q) => (
                  <button
                    key={q}
                    onClick={() => { setInput(q); inputRef.current?.focus(); }}
                    className="text-left text-[13px] p-4 rounded-2xl border border-slate-200/80 bg-white/70 hover:border-violet-300 hover:bg-white hover:shadow-md hover:shadow-violet-100/50 transition-all text-slate-600 leading-relaxed"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto px-6 py-6 space-y-5">
              {messages.map((msg, i) => {
                const isLast = i === messages.length - 1;
                const isStreamingActive = !!streamingContent;

                const getTraceProps = () => {
                  const meta = msg.metadata;
                  if (msg.role === "assistant" && meta && ((meta.timeline?.length ?? 0) > 0 || (meta.task_plan?.length ?? 0) > 0)) {
                    return { steps: meta.task_plan || [], stepThoughts: meta.step_thoughts || {}, timeline: meta.timeline || [] };
                  }
                  return null;
                };
                const traceProps = getTraceProps();

                return (
                  <div key={i}>
                    {msg.role === "user" && (
                      <ChatMessage role="user" content={msg.content} image={msg.image} attachments={msg.attachments} onDocRefClick={handleDocRefClick} />
                    )}
                    {msg.role === "assistant" && (
                      <div className="space-y-3">
                        {traceProps && (
                          <div className="ml-12">
                            <TaskProgress {...traceProps} />
                          </div>
                        )}
                        <ChatMessage role="assistant" content={msg.content} image={msg.image} attachments={msg.attachments} onDocRefClick={handleDocRefClick} />
                      </div>
                    )}
                  </div>
                );
              })}

              {streamingContent && (
                <div className="space-y-3">
                  {showTaskSteps && (agentTimeline.length > 0 || taskSteps.length > 0) && (
                    <div className="ml-12">
                      <TaskProgress steps={taskSteps} stepThoughts={stepThoughts} timeline={agentTimeline} continuingMessage={agentContinuingMessage} />
                    </div>
                  )}
                  <ChatMessage role="assistant" content={streamingContent} isStreaming onDocRefClick={handleDocRefClick} />
                </div>
              )}

              {isLoading && !streamingContent && agentTimeline.length > 0 && (
                <div className="ml-12">
                  <TaskProgress steps={taskSteps} stepThoughts={stepThoughts} timeline={agentTimeline} continuingMessage={agentContinuingMessage} />
                </div>
              )}

              {isLoading && !streamingContent && agentTimeline.length === 0 && (
                <ChatMessage role="assistant" content="" isStreaming />
              )}

              {/* Cost display */}
              {lastCost && (
                <div className="flex justify-center pt-2">
                  <span className="text-xs text-slate-500 bg-white/90 border border-slate-200/80 px-4 py-2 rounded-full shadow-sm font-medium">
                    {lastCost.cost > 0
                      ? `本次消耗 ¥${lastCost.cost.toFixed(2)} · 余额 ¥${lastCost.balance.toFixed(2)}`
                      : `免费额度 · 余额 ¥${lastCost.balance.toFixed(2)}`}
                  </span>
                </div>
              )}

              <div ref={endRef} />
            </div>
          )}
        </div>

        <div className="border-t border-slate-200/60 bg-white/95 backdrop-blur-sm px-4 py-4 shadow-[0_-4px_24px_-8px_rgba(0,0,0,0.06)]">
          <div className="max-w-3xl mx-auto">
            {costError && (
              <div className="mb-3 flex items-center gap-2 p-3.5 bg-red-50/90 border border-red-200/80 rounded-2xl text-sm text-red-700 shadow-sm">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span className="flex-1">{costError}</span>
                <a href="/profile" className="text-red-600 underline font-medium shrink-0">去充值</a>
                <button onClick={() => setCostError(null)} className="p-1 text-red-400 hover:text-red-600 hover:bg-red-100 rounded-lg transition-colors">×</button>
              </div>
            )}
            
            {/* 模式选择 */}
            <div className="flex flex-wrap items-center gap-4 mb-3">
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setDeepResearch(false)}
                  className={`relative flex flex-col items-center justify-center px-4 py-2 rounded-xl transition-all cursor-pointer min-w-[120px] ${
                    !deepResearch
                      ? "bg-gradient-to-r from-violet-500 to-indigo-500 text-white shadow-md shadow-violet-200/50"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200 border border-slate-200/60"
                  }`}
                >
                  <span className="text-sm font-semibold leading-tight">
                    快速响应
                  </span>
                  <span className="text-[10px] opacity-80 leading-tight">
                    自动·高效
                  </span>
                </button>
                <button
                  onClick={() => setDeepResearch(true)}
                  className={`relative flex flex-col items-center justify-center px-4 py-2 rounded-xl transition-all cursor-pointer min-w-[120px] ${
                    deepResearch
                      ? "bg-gradient-to-r from-violet-500 to-indigo-500 text-white shadow-md shadow-violet-200/50"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200 border border-slate-200/60"
                  }`}
                >
                  <span className="text-sm font-semibold leading-tight">
                    智能体模式
                  </span>
                  <span className="text-[10px] opacity-80 leading-tight">
                    多步骤·深入
                  </span>
                </button>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-xs text-slate-500">
                  {deepResearch ? (
                    <>
                      <span className="font-medium text-violet-600">● 智能体模式</span>
                      <span className="ml-2">允许长时间规划、多轮搜索和工具调用</span>
                    </>
                  ) : (
                    <>
                      <span className="font-medium text-slate-700">● 快速响应模式</span>
                      <span className="ml-2">系统自动判断，按需使用搜索和工具</span>
                    </>
                  )}
                </span>
              </div>
            </div>

            {imagePreview && (
              <div className="mb-2.5 relative inline-block">
                <img src={imagePreview} alt="预览" className="h-20 rounded-xl border border-slate-200/80 object-cover shadow-sm" />
                <button
                  onClick={removeImage}
                  className="absolute -top-1.5 -right-1.5 w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center text-sm hover:bg-red-600 shadow-md transition-colors"
                >
                  ×
                </button>
              </div>
            )}

            {attachments.length > 0 && (
              <div className="mb-2.5 flex flex-wrap gap-2">
                {attachments.map((attachment) => (
                  <div
                    key={attachment.id}
                    className="relative flex items-center gap-2.5 px-3 py-2 bg-slate-50 border border-slate-200/80 rounded-xl shadow-sm"
                  >
                    {attachment.preview ? (
                      <img src={attachment.preview} alt="" className="w-9 h-9 rounded-lg object-cover" />
                    ) : (
                      <div className="w-9 h-9 rounded-lg bg-slate-200/80 flex items-center justify-center">
                        <FileText className="w-4 h-4 text-slate-500" />
                      </div>
                    )}
                    <div className="flex flex-col min-w-0">
                      <span className="text-xs font-medium text-slate-700 max-w-28 truncate">{attachment.file.name}</span>
                      <span className="text-[10px] text-slate-400">{formatFileSize(attachment.file.size)}</span>
                    </div>
                    {attachment.uploading && (
                      <div className="w-4 h-4 border-2 border-violet-500 border-t-transparent rounded-full animate-spin shrink-0" />
                    )}
                    {!attachment.uploading && (
                      <button
                        onClick={() => removeAttachment(attachment.id)}
                        className="p-1 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors shrink-0"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}

            <div
              className={`flex items-end gap-2 rounded-2xl p-2.5 transition-all ${
                deepResearch
                  ? "bg-violet-50/80 border-2 border-violet-200/70 focus-within:border-violet-400 focus-within:ring-2 focus-within:ring-violet-100"
                  : "bg-slate-50/90 border border-slate-200/80 focus-within:border-violet-400 focus-within:ring-2 focus-within:ring-violet-100/50 focus-within:bg-white"
              }`}
            >
              <input
                ref={imageInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleImageSelect}
              />
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".pdf,.doc,.docx,.md,.txt,.png,.jpg,.jpeg,.gif"
                className="hidden"
                onChange={handleFileSelect}
              />
              {isLoading ? (
                <button
                  onClick={handleStop}
                  className="p-2.5 text-red-500 hover:text-red-600 rounded-xl hover:bg-red-50 shrink-0 transition-colors"
                  title="停止生成"
                >
                  <X className="w-5 h-5" />
                </button>
              ) : (
                <>
                  <button
                    onClick={() => imageInputRef.current?.click()}
                    className="p-2.5 text-slate-400 hover:text-slate-600 hover:bg-slate-200/80 rounded-xl shrink-0 transition-colors"
                    title="上传图片"
                  >
                    <ImagePlus className="w-5 h-5" />
                  </button>
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    className="p-2.5 text-slate-400 hover:text-slate-600 hover:bg-slate-200/80 rounded-xl shrink-0 transition-colors"
                    title="上传文件"
                  >
                    <Paperclip className="w-5 h-5" />
                  </button>
                </>
              )}
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={1}
                placeholder={deepResearch ? "描述你的智能体任务或拖拽论文..." : "输入你的问题或拖拽论文..."}
                className="flex-1 resize-none bg-transparent outline-none text-sm text-slate-800 placeholder-slate-400 max-h-32 py-2 px-1"
                style={{ minHeight: "38px" }}
                disabled={isLoading}
              />
              {isLoading ? (
                <button
                  onClick={handleStop}
                  className="p-2.5 bg-red-500 text-white rounded-xl hover:bg-red-600 transition-all shrink-0 shadow-md hover:shadow-lg"
                >
                  <X className="w-4 h-4" />
                </button>
              ) : (
                <button
                  onClick={handleSubmit}
                  disabled={(!input.trim() && !imagePreview && attachments.length === 0)}
                  className="p-2.5 bg-gradient-to-r from-violet-500 to-indigo-500 text-white rounded-xl hover:from-violet-600 hover:to-indigo-600 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg shrink-0"
                >
                  <Send className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
