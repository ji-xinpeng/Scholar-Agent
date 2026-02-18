"use client";

import { useState, useEffect } from "react";
import { User, GraduationCap, Building2, BookOpen, Star, Save, Edit3, Sparkles } from "lucide-react";
import { getProfile, updateProfile } from "@/lib/api";

const KNOWLEDGE_LEVELS = [
  { value: "beginner", label: "初级" },
  { value: "intermediate", label: "中级" },
  { value: "advanced", label: "高级" },
];

export default function ProfilePage() {
  const [profile, setProfile] = useState<any>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<any>({});
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState("");

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    const data = await getProfile();
    setProfile(data);
    setForm(data);
  };

  const handleSave = async () => {
    setSaving(true);
    await updateProfile({
      display_name: form.display_name,
      research_field: form.research_field,
      institution: form.institution,
      knowledge_level: form.knowledge_level,
      bio: form.bio,
    });
    await loadProfile();
    setSaving(false);
    setEditing(false);
    showToast("个人资料保存成功！");
  };

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(""), 3000);
  };

  if (!profile) return <div className="flex-1 flex items-center justify-center text-gray-400">加载中...</div>;

  return (
    <div className="flex-1 overflow-y-auto bg-gray-50">
      {toast && (
        <div className="fixed top-20 left-1/2 -translate-x-1/2 bg-green-500 text-white px-4 py-2 rounded-lg text-sm shadow-lg z-50 animate-fade-in">
          {toast}
        </div>
      )}

      <div className="max-w-4xl mx-auto p-6 grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-1 space-y-4">
          <div className="bg-white rounded-2xl border border-gray-200 p-6 text-center">
            <div className="w-20 h-20 rounded-full bg-gradient-to-br from-indigo-400 to-purple-500 flex items-center justify-center mx-auto mb-4">
              <User className="w-10 h-10 text-white" />
            </div>
            <h3 className="font-semibold text-gray-800">{profile.display_name}</h3>
            <p className="text-sm text-gray-500 mt-1">{profile.research_field || "未设置研究方向"}</p>
            <p className="text-xs text-gray-400 mt-1">{profile.institution || "未设置机构"}</p>
            <div className="mt-4 flex justify-center">
              <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium bg-indigo-100 text-indigo-700">
                <Star className="w-3 h-3" />
                {KNOWLEDGE_LEVELS.find((l) => l.value === profile.knowledge_level)?.label || profile.knowledge_level}
              </span>
            </div>
          </div>
        </div>

        <div className="md:col-span-2 space-y-4">
          <div className="bg-white rounded-2xl border border-gray-200 p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-base font-semibold text-gray-800">个人信息</h3>
              {!editing ? (
                <button onClick={() => setEditing(true)} className="flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-700">
                  <Edit3 className="w-4 h-4" /> 编辑
                </button>
              ) : (
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="flex items-center gap-1 text-sm bg-indigo-500 text-white px-3 py-1.5 rounded-lg hover:bg-indigo-600 disabled:opacity-50"
                >
                  <Save className="w-4 h-4" /> {saving ? "保存中..." : "保存"}
                </button>
              )}
            </div>

            <div className="space-y-4">
              <Field icon={<User className="w-4 h-4" />} label="显示名称">
                {editing ? (
                  <input value={form.display_name || ""} onChange={(e) => setForm({ ...form, display_name: e.target.value })} className="input-field" />
                ) : (
                  <span className="text-sm text-gray-800">{profile.display_name}</span>
                )}
              </Field>

              <Field icon={<BookOpen className="w-4 h-4" />} label="研究方向">
                {editing ? (
                  <input value={form.research_field || ""} onChange={(e) => setForm({ ...form, research_field: e.target.value })} className="input-field" placeholder="例如：计算机视觉、自然语言处理" />
                ) : (
                  <span className="text-sm text-gray-800">{profile.research_field || "-"}</span>
                )}
              </Field>

              <Field icon={<Building2 className="w-4 h-4" />} label="所属机构">
                {editing ? (
                  <input value={form.institution || ""} onChange={(e) => setForm({ ...form, institution: e.target.value })} className="input-field" placeholder="例如：清华大学、北京大学" />
                ) : (
                  <span className="text-sm text-gray-800">{profile.institution || "-"}</span>
                )}
              </Field>

              <Field icon={<GraduationCap className="w-4 h-4" />} label="知识水平">
                {editing ? (
                  <select value={form.knowledge_level || "intermediate"} onChange={(e) => setForm({ ...form, knowledge_level: e.target.value })} className="input-field">
                    {KNOWLEDGE_LEVELS.map((l) => (
                      <option key={l.value} value={l.value}>{l.label}</option>
                    ))}
                  </select>
                ) : (
                  <span className="text-sm text-gray-800">{KNOWLEDGE_LEVELS.find((l) => l.value === profile.knowledge_level)?.label || profile.knowledge_level}</span>
                )}
              </Field>

              <Field icon={<Sparkles className="w-4 h-4" />} label="个人简介">
                {editing ? (
                  <textarea value={form.bio || ""} onChange={(e) => setForm({ ...form, bio: e.target.value })} className="input-field" rows={3} placeholder="介绍一下你的研究方向..." />
                ) : (
                  <span className="text-sm text-gray-800">{profile.bio || "-"}</span>
                )}
              </Field>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function Field({ icon, label, children }: { icon: React.ReactNode; label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3">
      <div className="mt-2 text-gray-400">{icon}</div>
      <div className="flex-1">
        <label className="text-xs text-gray-500 font-medium">{label}</label>
        <div className="mt-1">{children}</div>
      </div>
    </div>
  );
}
