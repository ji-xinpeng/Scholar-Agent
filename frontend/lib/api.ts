// 本地开发时设置 NEXT_PUBLIC_BACKEND_URL 可直连后端，避免经 Next 代理缓冲导致 SSE 不流式
const API_BASE =
  typeof process !== "undefined" && process.env.NEXT_PUBLIC_BACKEND_URL
    ? `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1`
    : "/api/v1";

import { getUserId } from "./auth";

// ========== 登录 / 注册 ==========
export async function login(username: string, password: string): Promise<{ user_id: string; username: string }> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "登录失败");
  return data;
}

export async function register(
  username: string,
  password: string,
  confirm_password: string
): Promise<{ user_id: string; username: string }> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password, confirm_password }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "注册失败");
  return data;
}

// ========== 聊天 / 会话 ==========
export async function fetchSSEChat(
  message: string,
  sessionId: string | null,
  deepResearch: boolean,
  onEvent: (event: { type: string; data: any }) => void,
  onDone: () => void,
  documentIds?: string[],
  signal?: AbortSignal,
  /** 当前轮次用户选中的图片（data URL），用于视觉问答 */
  imageData?: string | null,
): Promise<string | null> {
  const body: any = {
    message,
    session_id: sessionId,
    user_id: getUserId(),
    deep_research: deepResearch,
  };
  if (documentIds && documentIds.length > 0) {
    body.document_ids = documentIds;
  }
  if (imageData) {
    body.image_data = imageData;
  }

  const res = await fetch(`${API_BASE}/chat/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });

  // 处理 402 余额不足等错误
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: { message: "请求失败" } }));
    onDone();
    const error: any = new Error(err.detail?.message || "请求失败");
    error.status = res.status;
    error.detail = err.detail;
    throw error;
  }

  const newSessionId = res.headers.get("X-Session-Id");
  if (!res.body) {
    onDone();
    return newSessionId;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const parts = buffer.split("\n\n");
      buffer = parts.pop() || "";

      for (const part of parts) {
        const lines = part.split("\n");
        let eventType = "";
        let data = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) eventType = line.slice(7);
          if (line.startsWith("data: ")) data = line.slice(6);
        }
        if (eventType && data) {
          try {
            onEvent({ type: eventType, data: JSON.parse(data) });
          } catch {}
        }
      }
    }
  } catch (e: any) {
    if (e.name !== "AbortError") {
      throw e;
    }
  } finally {
    onDone();
  }
  return newSessionId;
}

export async function getSessions(userId?: string) {
  const uid = userId ?? getUserId();
  const res = await fetch(`${API_BASE}/chat/sessions?user_id=${uid}`);
  return res.json();
}

export async function createSession(userId?: string, mode = "normal") {
  const uid = userId ?? getUserId();
  const res = await fetch(`${API_BASE}/chat/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: uid, title: "新建对话", mode }),
  });
  return res.json();
}

export async function deleteSession(sessionId: string, userId?: string) {
  const uid = userId ?? getUserId();
  const res = await fetch(`${API_BASE}/chat/sessions/${sessionId}?user_id=${uid}`, { method: "DELETE" });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || "删除失败");
  }
}

export async function getMessages(sessionId: string, userId?: string) {
  const uid = userId ?? getUserId();
  const res = await fetch(`${API_BASE}/chat/sessions/${sessionId}/messages?user_id=${uid}`);
  return res.json();
}

// ========== 文档 ==========
export async function uploadDocument(file: File, folderId?: string) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("user_id", getUserId());
  if (folderId) formData.append("folder_id", folderId);
  const res = await fetch(`${API_BASE}/documents/upload`, { method: "POST", body: formData });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = typeof data.detail === "string" ? data.detail : data.detail?.message || "上传失败";
    throw new Error(msg);
  }
  return data;
}

export async function getDocuments(page = 1, pageSize = 10, folderId?: string) {
  let url = `${API_BASE}/documents/?user_id=${getUserId()}&page=${page}&page_size=${pageSize}`;
  if (folderId) url += `&folder_id=${folderId}`;
  const res = await fetch(url);
  return res.json();
}

export async function deleteDocument(docId: string) {
  await fetch(`${API_BASE}/documents/${docId}`, { method: "DELETE" });
}

export async function getDocumentContent(docId: string) {
  const res = await fetch(`${API_BASE}/documents/${docId}/content`);
  return res.json();
}

export async function updateDocumentContent(docId: string, content: string) {
  const res = await fetch(`${API_BASE}/documents/${docId}/content`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = typeof data.detail === "string" ? data.detail : data.detail?.message || "保存失败";
    throw new Error(msg);
  }
  return data;
}

export async function createFolder(name: string, parentId?: string) {
  const res = await fetch(`${API_BASE}/documents/folders`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: getUserId(), name, parent_id: parentId || null }),
  });
  return res.json();
}

export async function getFolders() {
  const res = await fetch(`${API_BASE}/documents/folders/list?user_id=${getUserId()}`);
  return res.json();
}

export async function deleteFolder(folderId: string) {
  await fetch(`${API_BASE}/documents/folders/${folderId}`, { method: "DELETE" });
}

// ========== 用户 ==========
export async function getProfile(userId?: string) {
  const uid = userId ?? getUserId();
  const res = await fetch(`${API_BASE}/users/profile?user_id=${uid}`);
  return res.json();
}

export async function updateProfile(data: Record<string, any>, userId?: string) {
  const uid = userId ?? getUserId();
  const res = await fetch(`${API_BASE}/users/profile?user_id=${uid}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function recharge(amount: number, userId?: string) {
  const uid = userId ?? getUserId();
  const res = await fetch(`${API_BASE}/users/recharge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: uid, amount }),
  });
  return res.json();
}

// ========== 费用 ==========
export async function getUsageStats(userId?: string) {
  const uid = userId ?? getUserId();
  const res = await fetch(`${API_BASE}/users/usage?user_id=${uid}`);
  return res.json();
}

export async function getUsageRecords(userId?: string, page = 1, pageSize = 20) {
  const uid = userId ?? getUserId();
  const res = await fetch(`${API_BASE}/users/usage/records?user_id=${uid}&page=${page}&page_size=${pageSize}`);
  return res.json();
}
