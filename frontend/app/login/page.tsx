"use client";

import { useState } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { GraduationCap } from "lucide-react";

export default function LoginPage() {
  const { login, register } = useAuth();
  const [isRegister, setIsRegister] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (!username.trim()) {
      setError("请输入用户名");
      return;
    }
    if (!password) {
      setError("请输入密码");
      return;
    }
    if (isRegister && password !== confirmPassword) {
      setError("两次输入的密码不一致");
      return;
    }
    setSubmitting(true);
    try {
      if (isRegister) {
        await register(username.trim(), password, confirmPassword);
      } else {
        await login(username.trim(), password);
      }
    } catch (err: any) {
      setError(err?.message || "操作失败，请重试");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col items-center justify-center min-h-0 bg-gradient-to-br from-slate-50 via-violet-50/30 to-indigo-50/50 px-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-200/50 mb-4">
            <GraduationCap className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
            Scholar Agent
          </h1>
          <p className="text-slate-500 text-sm mt-1">AI 学术研究助手</p>
        </div>

        <div className="bg-white/90 backdrop-blur border border-slate-200/80 rounded-2xl shadow-xl shadow-slate-200/50 p-6">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">
            {isRegister ? "注册账号" : "登录"}
          </h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1.5">用户名</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="请输入用户名"
                className="input-field"
                autoComplete="username"
                disabled={submitting}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-600 mb-1.5">密码</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="请输入密码"
                className="input-field"
                autoComplete={isRegister ? "new-password" : "current-password"}
                disabled={submitting}
              />
            </div>
            {isRegister && (
              <div>
                <label className="block text-sm font-medium text-slate-600 mb-1.5">确认密码</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="请再次输入密码"
                  className="input-field"
                  autoComplete="new-password"
                  disabled={submitting}
                />
              </div>
            )}
            {error && (
              <div className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
                {error}
              </div>
            )}
            <button
              type="submit"
              disabled={submitting}
              className="w-full py-2.5 rounded-xl bg-gradient-to-r from-violet-500 to-indigo-500 text-white font-medium shadow-md hover:from-violet-600 hover:to-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {submitting ? "请稍候..." : isRegister ? "注册" : "登录"}
            </button>
          </form>
          <p className="mt-4 text-center text-sm text-slate-500">
            {isRegister ? "已有账号？" : "还没有账号？"}
            <button
              type="button"
              onClick={() => {
                setIsRegister(!isRegister);
                setError("");
              }}
              className="ml-1 text-indigo-600 font-medium hover:underline"
            >
              {isRegister ? "去登录" : "去注册"}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
