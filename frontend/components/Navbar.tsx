"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BookOpen, FileText, User, GraduationCap } from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "智能助手", icon: BookOpen },
  { href: "/documents", label: "文档管理", icon: FileText },
  { href: "/profile", label: "个人中心", icon: User },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center px-6 shrink-0 z-30">
      <Link href="/" className="flex items-center gap-2 mr-8">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
          <GraduationCap className="w-5 h-5 text-white" />
        </div>
        <span className="text-lg font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
          Scholar Agent
        </span>
      </Link>
      <nav className="flex items-center gap-1">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                active
                  ? "bg-indigo-50 text-indigo-700"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
