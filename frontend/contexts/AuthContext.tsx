"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { useRouter, usePathname } from "next/navigation";
import {
  getStoredUser,
  setStoredUser,
  clearStoredUser,
  type AuthUser,
} from "@/lib/auth";
import { login as apiLogin, register as apiRegister } from "@/lib/api";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string, confirmPassword: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    setUser(getStoredUser());
    setLoading(false);
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const res = await apiLogin(username, password);
    const u = { user_id: res.user_id, username: res.username };
    setStoredUser(u);
    setUser(u);
    router.push("/");
  }, [router]);

  const register = useCallback(
    async (username: string, password: string, confirmPassword: string) => {
      const res = await apiRegister(username, password, confirmPassword);
      const u = { user_id: res.user_id, username: res.username };
      setStoredUser(u);
      setUser(u);
      router.push("/");
    },
    [router]
  );

  const logout = useCallback(() => {
    clearStoredUser();
    setUser(null);
    router.push("/login");
  }, [router]);

  useEffect(() => {
    if (loading) return;
    const isLoginPage = pathname === "/login";
    if (!user && !isLoginPage) {
      router.replace("/login");
      return;
    }
    if (user && isLoginPage) {
      router.replace("/");
    }
  }, [user, loading, pathname, router]);

  const isLoginPage = pathname === "/login";

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {loading && !isLoginPage && !user ? (
        <div className="flex flex-1 items-center justify-center text-slate-500 text-sm">
          加载中...
        </div>
      ) : (
        children
      )}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
