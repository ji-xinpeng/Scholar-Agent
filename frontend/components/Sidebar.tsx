"use client";

import { useState, useEffect } from "react";
import { Plus, MessageSquare, Trash2, ChevronLeft, ChevronRight } from "lucide-react";
import { getSessions, createSession, deleteSession } from "@/lib/api";
import { formatDate } from "@/lib/utils";

interface SidebarProps {
  currentSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
}

export default function Sidebar({ currentSessionId, onSelectSession, onNewChat }: SidebarProps) {
  const [sessions, setSessions] = useState<any[]>([]);
  const [collapsed, setCollapsed] = useState(false);

  const loadSessions = async () => {
    try {
      const data = await getSessions();
      setSessions(data.sessions || []);
    } catch {}
  };

  useEffect(() => {
    loadSessions();
  }, [currentSessionId]);

  const handleNew = async () => {
    onNewChat();
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    await deleteSession(id);
    loadSessions();
    if (currentSessionId === id) {
      onNewChat();
    }
  };

  if (collapsed) {
    return (
      <div className="w-12 bg-gray-50 border-r border-gray-200 flex flex-col items-center py-3 gap-2 shrink-0">
        <button onClick={() => setCollapsed(false)} className="p-2 hover:bg-gray-200 rounded-lg" title="展开">
          <ChevronRight className="w-4 h-4 text-gray-500" />
        </button>
        <button onClick={handleNew} className="p-2 hover:bg-gray-200 rounded-lg" title="新建对话">
          <Plus className="w-4 h-4 text-gray-500" />
        </button>
      </div>
    );
  }

  return (
    <div className="w-64 bg-gray-50 border-r border-gray-200 flex flex-col shrink-0">
      <div className="p-3 flex items-center justify-between border-b border-gray-200">
        <span className="text-sm font-semibold text-gray-700">历史记录</span>
        <div className="flex items-center gap-1">
          <button onClick={handleNew} className="p-1.5 hover:bg-gray-200 rounded-lg" title="新建对话">
            <Plus className="w-4 h-4 text-gray-500" />
          </button>
          <button onClick={() => setCollapsed(true)} className="p-1.5 hover:bg-gray-200 rounded-lg" title="收起">
            <ChevronLeft className="w-4 h-4 text-gray-500" />
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {sessions.length === 0 ? (
          <div className="text-xs text-gray-400 text-center mt-8">暂无对话记录</div>
        ) : (
          sessions.map((s) => (
            <div
              key={s.id}
              onClick={() => onSelectSession(s.id)}
              className={`group flex items-center gap-2 p-2 rounded-lg cursor-pointer text-sm transition-colors ${
                currentSessionId === s.id
                  ? "bg-indigo-100 text-indigo-800"
                  : "text-gray-700 hover:bg-gray-100"
              }`}
            >
              <MessageSquare className="w-4 h-4 shrink-0 opacity-50" />
              <div className="flex-1 min-w-0">
                <div className="truncate text-sm">{s.title}</div>
                <div className="text-xs text-gray-400">{formatDate(s.updated_at)}</div>
              </div>
              <button
                onClick={(e) => handleDelete(e, s.id)}
                className="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-red-100 transition-opacity"
              >
                <Trash2 className="w-3.5 h-3.5 text-red-400" />
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
