import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";
import { AuthProvider } from "@/contexts/AuthContext";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Scholar Agent - AI 学术研究助手",
  description: "AI驱动的智能学术研究助手，支持文献综述、论文搜索、研究规划。",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh">
      <body className={inter.className}>
        <AuthProvider>
          <div className="flex flex-col h-screen bg-gray-50">
            <Navbar />
            <main className="flex flex-1 overflow-hidden">{children}</main>
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}
