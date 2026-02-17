"use client";

import { useState, useEffect, useRef } from "react";
import {
  Upload, FolderPlus, Trash2, FileText, File, FolderOpen,
  ChevronLeft, ChevronRight, Search, MoreVertical, Folder,
} from "lucide-react";
import {
  uploadDocument, getDocuments, deleteDocument,
  createFolder, getFolders, deleteFolder,
} from "@/lib/api";
import { formatFileSize, formatDate } from "@/lib/utils";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<any[]>([]);
  const [folders, setFolders] = useState<any[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [pageSize] = useState(10);
  const [uploading, setUploading] = useState(false);
  const [showNewFolder, setShowNewFolder] = useState(false);
  const [newFolderName, setNewFolderName] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadData = async () => {
    try {
      const [docsRes, foldersRes] = await Promise.all([
        getDocuments(page, pageSize, selectedFolder || undefined),
        getFolders(),
      ]);
      setDocuments(docsRes.documents || []);
      setTotal(docsRes.total || 0);
      setFolders(foldersRes.folders || []);
    } catch {}
  };

  useEffect(() => { loadData(); }, [page, selectedFolder]);

  const handleUpload = async (files: FileList | null) => {
    if (!files) return;
    setUploading(true);
    for (const file of Array.from(files)) {
      await uploadDocument(file, selectedFolder || undefined);
    }
    setUploading(false);
    loadData();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    handleUpload(e.dataTransfer.files);
  };

  const handleDelete = async (docId: string) => {
    await deleteDocument(docId);
    loadData();
  };

  const handleCreateFolder = async () => {
    if (!newFolderName.trim()) return;
    await createFolder(newFolderName.trim());
    setNewFolderName("");
    setShowNewFolder(false);
    loadData();
  };

  const handleDeleteFolder = async (folderId: string) => {
    await deleteFolder(folderId);
    if (selectedFolder === folderId) setSelectedFolder(null);
    loadData();
  };

  const totalPages = Math.ceil(total / pageSize);
  const fileIcon = (type: string) => type === "pdf" ? <FileText className="w-5 h-5 text-red-400" /> : <File className="w-5 h-5 text-blue-400" />;

  const filtered = searchQuery
    ? documents.filter((d) => d.original_name.toLowerCase().includes(searchQuery.toLowerCase()))
    : documents;

  return (
    <div className="flex flex-1 overflow-hidden">
      {/* 文件夹侧边栏 */}
      <div className="w-60 bg-gray-50 border-r border-gray-200 flex flex-col shrink-0">
        <div className="p-3 border-b border-gray-200">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-gray-700">文件夹</span>
            <button onClick={() => setShowNewFolder(true)} className="p-1 hover:bg-gray-200 rounded" title="新建文件夹">
              <FolderPlus className="w-4 h-4 text-gray-500" />
            </button>
          </div>
          {showNewFolder && (
            <div className="flex gap-1 mt-2">
              <input
                autoFocus
                value={newFolderName}
                onChange={(e) => setNewFolderName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreateFolder()}
                placeholder="文件夹名称"
                className="flex-1 text-sm border rounded px-2 py-1 outline-none focus:border-indigo-400"
              />
              <button onClick={handleCreateFolder} className="text-xs px-2 py-1 bg-indigo-500 text-white rounded hover:bg-indigo-600">
                添加
              </button>
            </div>
          )}
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          <div
            onClick={() => { setSelectedFolder(null); setPage(1); }}
            className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer text-sm transition-colors ${
              !selectedFolder ? "bg-indigo-100 text-indigo-700" : "text-gray-600 hover:bg-gray-100"
            }`}
          >
            <FolderOpen className="w-4 h-4" />
            <span>全部文档</span>
          </div>
          {folders.map((f) => (
            <div
              key={f.id}
              onClick={() => { setSelectedFolder(f.id); setPage(1); }}
              className={`group flex items-center gap-2 p-2 rounded-lg cursor-pointer text-sm transition-colors ${
                selectedFolder === f.id ? "bg-indigo-100 text-indigo-700" : "text-gray-600 hover:bg-gray-100"
              }`}
            >
              <Folder className="w-4 h-4" />
              <span className="flex-1 truncate">{f.name}</span>
              <span className="text-xs text-gray-400">{f.document_count}</span>
              <button
                onClick={(e) => { e.stopPropagation(); handleDeleteFolder(f.id); }}
                className="p-0.5 rounded opacity-0 group-hover:opacity-100 hover:bg-red-100"
              >
                <Trash2 className="w-3 h-3 text-red-400" />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* 主内容 */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* 上传区域 */}
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          className="m-4 mb-0 border-2 border-dashed border-gray-300 rounded-xl p-6 text-center hover:border-indigo-400 hover:bg-indigo-50 transition-colors cursor-pointer"
          onClick={() => fileInputRef.current?.click()}
        >
          <input ref={fileInputRef} type="file" multiple accept=".pdf,.doc,.docx,.md,.txt" className="hidden" onChange={(e) => handleUpload(e.target.files)} />
          <Upload className={`w-8 h-8 mx-auto mb-2 ${uploading ? "text-indigo-500 animate-bounce" : "text-gray-400"}`} />
          <p className="text-sm text-gray-600 font-medium">
            {uploading ? "上传中..." : "拖拽文件到此处或点击上传"}
          </p>
          <p className="text-xs text-gray-400 mt-1">支持 PDF、Word、Markdown、Text 格式</p>
        </div>

        {/* 搜索 */}
        <div className="px-4 pt-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="搜索文档..."
              className="w-full pl-10 pr-4 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-indigo-400 focus:ring-1 focus:ring-indigo-200"
            />
          </div>
        </div>

        {/* 文档列表 */}
        <div className="flex-1 overflow-y-auto p-4">
          {filtered.length === 0 ? (
            <div className="text-center text-gray-400 text-sm mt-12">暂无文档</div>
          ) : (
            <div className="space-y-2">
              {filtered.map((doc) => (
                <div key={doc.id} className="flex items-center gap-3 p-3 bg-white border border-gray-200 rounded-xl hover:shadow-sm transition-shadow group">
                  {fileIcon(doc.file_type)}
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-gray-800 truncate">{doc.original_name}</div>
                    <div className="text-xs text-gray-400 mt-0.5">
                      {formatFileSize(doc.file_size)} &middot; {formatDate(doc.created_at)} &middot; {doc.file_type.toUpperCase()}
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(doc.id)}
                    className="p-1.5 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-red-50 transition-opacity"
                  >
                    <Trash2 className="w-4 h-4 text-red-400" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 分页 */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 p-4 border-t border-gray-200">
            <button
              onClick={() => setPage(Math.max(1, page - 1))}
              disabled={page === 1}
              className="p-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-30"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
              <button
                key={p}
                onClick={() => setPage(p)}
                className={`w-8 h-8 rounded-lg text-sm font-medium transition-colors ${
                  page === p ? "bg-indigo-500 text-white" : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                {p}
              </button>
            ))}
            <button
              onClick={() => setPage(Math.min(totalPages, page + 1))}
              disabled={page === totalPages}
              className="p-1.5 rounded-lg border border-gray-200 hover:bg-gray-50 disabled:opacity-30"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
            <span className="text-xs text-gray-400 ml-2">共计: {total}</span>
          </div>
        )}
      </div>
    </div>
  );
}
