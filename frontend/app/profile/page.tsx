"use client";

import { useState, useEffect } from "react";
import {
  User, GraduationCap, Building2, BookOpen, Star, CreditCard,
  Save, Edit3, Sparkles, BarChart3, Zap, MessageSquare,
} from "lucide-react";
import { getProfile, updateProfile, recharge, getUsageStats } from "@/lib/api";

const KNOWLEDGE_LEVELS = [
  { value: "beginner", label: "初级" },
  { value: "intermediate", label: "中级" },
  { value: "advanced", label: "高级" },
];

const RECHARGE_OPTIONS = [50, 100, 200];

export default function ProfilePage() {
  const [profile, setProfile] = useState<any>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<any>({});
  const [customAmount, setCustomAmount] = useState("");
  const [saving, setSaving] = useState(false);
  const [recharging, setRecharging] = useState(false);
  const [toast, setToast] = useState("");
  const [usage, setUsage] = useState<any>(null);

  useEffect(() => {
    loadProfile();
    loadUsage();
  }, []);

  const loadProfile = async () => {
    const data = await getProfile();
    setProfile(data);
    setForm(data);
  };

  const loadUsage = async () => {
    try { setUsage(await getUsageStats()); } catch {}
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

  const handleRecharge = async (amount: number) => {
    setRecharging(true);
    await recharge(amount);
    await loadProfile();
    await loadUsage();
    setRecharging(false);
    showToast(`充值 ¥${amount} 成功！`);
  };

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(""), 3000);
  };

  if (!profile) return <div className="flex-1 flex items-center justify-center text-gray-400">加载中...</div>;

  return (
    <div className="flex-1 overflow-y-auto bg-gray-50">
      {/* 提示 */}
      {toast && (
        <div className="fixed top-20 left-1/2 -translate-x-1/2 bg-green-500 text-white px-4 py-2 rounded-lg text-sm shadow-lg z-50 animate-fade-in">
          {toast}
        </div>
      )}

      <div className="max-w-4xl mx-auto p-6 grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* 左侧面板 - 个人信息 */}
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
                {profile.knowledge_level}
              </span>
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-gray-200 p-4">
            <div className="flex items-center gap-2 mb-2">
              <CreditCard className="w-4 h-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-700">账户</span>
            </div>
            <div className="flex items-center justify-between mt-2">
              <span className="text-xs text-gray-500">模式</span>
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                profile.model_mode === "paid" ? "bg-amber-100 text-amber-700" : "bg-gray-100 text-gray-600"
              }`}>
                {profile.model_mode === "paid" ? "付费" : "免费"}
              </span>
            </div>
            <div className="flex items-center justify-between mt-2">
              <span className="text-xs text-gray-500">余额</span>
              <span className="text-sm font-semibold text-gray-800">¥{(profile.balance || 0).toFixed(2)}</span>
            </div>
          </div>

          {/* 用量统计卡片 */}
          {usage && (
            <div className="bg-white rounded-2xl border border-gray-200 p-4">
              <div className="flex items-center gap-2 mb-3">
                <BarChart3 className="w-4 h-4 text-gray-500" />
                <span className="text-sm font-medium text-gray-700">用量统计</span>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500">今日对话</span>
                  <span className="text-xs font-medium text-gray-800">{usage.today.count} 次</span>
                </div>
                {usage.today.free_remaining !== null && (
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-500">免费剩余</span>
                    <span className={`text-xs font-medium ${usage.today.free_remaining > 5 ? "text-green-600" : usage.today.free_remaining > 0 ? "text-amber-600" : "text-red-600"}`}>
                      {usage.today.free_remaining}/{usage.today.free_quota} 次
                    </span>
                  </div>
                )}
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500">今日费用</span>
                  <span className="text-xs font-medium text-gray-800">¥{usage.today.cost.toFixed(2)}</span>
                </div>
                <div className="border-t border-gray-100 pt-2 mt-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-500">累计对话</span>
                    <span className="text-xs font-medium text-gray-800">{usage.total.count} 次</span>
                  </div>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-xs text-gray-500">累计费用</span>
                    <span className="text-xs font-medium text-gray-800">¥{usage.total.cost.toFixed(2)}</span>
                  </div>
                </div>
                <div className="border-t border-gray-100 pt-2 mt-2 space-y-1">
                  <div className="text-xs text-gray-400">定价</div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-500 flex items-center gap-1"><MessageSquare className="w-3 h-3" /> 普通模式</span>
                    <span className="text-xs text-gray-600">¥{usage.pricing.normal}/次</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-500 flex items-center gap-1"><Zap className="w-3 h-3" /> 智能体模式</span>
                    <span className="text-xs text-gray-600">¥{usage.pricing.agent}/次</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 右侧面板 - 编辑与充值 */}
        <div className="md:col-span-2 space-y-4">
          {/* 资料编辑 */}
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

          {/* 模型与充值 */}
          <div className="bg-white rounded-2xl border border-gray-200 p-6">
            <h3 className="text-base font-semibold text-gray-800 mb-4">模型设置与充值</h3>

            <div className="grid grid-cols-2 gap-3 mb-4">
              <div
                className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
                  profile.model_mode === "free" ? "border-indigo-500 bg-indigo-50" : "border-gray-200 hover:border-gray-300"
                }`}
                onClick={async () => { await updateProfile({ model_mode: "free" }); await loadProfile(); }}
              >
                <div className="text-sm font-semibold text-gray-800">免费模式</div>
                <div className="text-xs text-gray-500 mt-1">基础功能，有使用限制</div>
              </div>
              <div
                className={`p-4 rounded-xl border-2 cursor-pointer transition-all ${
                  profile.model_mode === "paid" ? "border-amber-500 bg-amber-50" : "border-gray-200 hover:border-gray-300"
                }`}
                onClick={async () => { await updateProfile({ model_mode: "paid" }); await loadProfile(); }}
              >
                <div className="text-sm font-semibold text-gray-800">付费模式</div>
                <div className="text-xs text-gray-500 mt-1">无限制使用，高级模型</div>
              </div>
            </div>

            <div className="border-t border-gray-100 pt-4">
              <div className="text-sm font-medium text-gray-700 mb-3">充值余额</div>
              <div className="flex flex-wrap gap-2">
                {RECHARGE_OPTIONS.map((amt) => (
                  <button
                    key={amt}
                    onClick={() => handleRecharge(amt)}
                    disabled={recharging}
                    className="px-4 py-2 rounded-lg border border-gray-200 text-sm font-medium text-gray-700 hover:bg-indigo-50 hover:border-indigo-300 hover:text-indigo-700 transition-colors disabled:opacity-50"
                  >
                    ¥{amt}
                  </button>
                ))}
                <div className="flex items-center gap-1">
                  <input
                    value={customAmount}
                    onChange={(e) => setCustomAmount(e.target.value.replace(/[^0-9.]/g, ""))}
                    placeholder="自定义"
                    className="w-24 px-3 py-2 text-sm border border-gray-200 rounded-lg outline-none focus:border-indigo-400"
                  />
                  <button
                    onClick={() => { const amt = parseFloat(customAmount); if (amt > 0) { handleRecharge(amt); setCustomAmount(""); } }}
                    disabled={recharging || !customAmount}
                    className="px-3 py-2 bg-indigo-500 text-white text-sm rounded-lg hover:bg-indigo-600 disabled:opacity-50"
                  >
                    支付
                  </button>
                </div>
              </div>
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
