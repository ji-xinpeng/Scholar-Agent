"use client";

import { useState } from "react";
import { CheckCircle2, Circle, Loader2, ChevronRight, ChevronDown, X } from "lucide-react";

export interface TaskStep {
  id: string;
  action: string;
  status: "pending" | "running" | "done";
  progress?: number;
  message?: string;
}

interface TaskProgressProps {
  steps: TaskStep[];
  agentThought?: string;
  stepThoughts?: Record<string, string>;
}

export default function TaskProgress({ steps, agentThought = "", stepThoughts = {} }: TaskProgressProps) {
  const [thoughtExpanded, setThoughtExpanded] = useState(true);
  const [expandedSteps, setExpandedSteps] = useState<Record<string, boolean>>({});

  if (steps.length === 0) return null;

  const doneCount = steps.filter((s) => s.status === "done").length;

  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm max-w-[85%] overflow-hidden">
      {/* 思考过程 - 可折叠 */}
      {agentThought && (
        <div className="border-b border-gray-100">
          <button
            onClick={() => setThoughtExpanded(!thoughtExpanded)}
            className="w-full flex items-center gap-2 px-4 py-3 text-left hover:bg-gray-50 transition-colors"
          >
            {thoughtExpanded ? (
              <ChevronDown className="w-4 h-4 text-gray-500 shrink-0" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-500 shrink-0" />
            )}
            <span className="text-sm font-medium text-gray-700">思考过程</span>
          </button>
          {thoughtExpanded && (
            <div className="px-4 pb-3 pt-0 pl-10">
              <p className="text-sm text-gray-600 leading-relaxed">{agentThought}</p>
            </div>
          )}
        </div>
      )}

      {/* 行动计划 - 进度与清单 */}
      <div className="p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            行动计划
          </span>
          <span className="text-xs text-gray-400">
            {doneCount}/{steps.length} 已完成
          </span>
        </div>

        <div className="space-y-1">
          {steps.map((step) => {
            const thought = stepThoughts[step.id];
            const hasThought = !!thought && step.status === "done";
            const stepExpanded = expandedSteps[step.id] ?? true;

            return (
              <div key={step.id} className="rounded-lg border border-gray-100 overflow-hidden">
                {/* 步骤行 */}
                <div className="flex items-start gap-2.5 px-3 py-2.5">
                  {step.status === "done" ? (
                    <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                  ) : step.status === "running" ? (
                    <Loader2 className="w-4 h-4 text-indigo-500 animate-spin mt-0.5 shrink-0" />
                  ) : (
                    <Circle className="w-4 h-4 text-gray-300 mt-0.5 shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <div
                      className={`text-sm ${
                        step.status === "done"
                          ? "text-gray-600"
                          : step.status === "running"
                          ? "text-indigo-700 font-medium"
                          : "text-gray-400"
                      }`}
                    >
                      {step.action}
                    </div>
                    {step.status === "running" && step.progress !== undefined && (
                      <div className="mt-1.5">
                        <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-indigo-500 rounded-full transition-all duration-300"
                            style={{ width: `${step.progress * 100}%` }}
                          />
                        </div>
                        {step.message && (
                          <div className="text-xs text-gray-400 mt-1">{step.message}</div>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                {/* Thought 块 - 步骤完成后的执行详情 */}
                {hasThought && (
                  <div className="border-t border-gray-50 bg-gray-50/50">
                    <button
                      onClick={() =>
                        setExpandedSteps((p) => ({ ...p, [step.id]: !stepExpanded }))
                      }
                      className="w-full flex items-center gap-2 px-4 py-2 text-left hover:bg-gray-50/80 transition-colors"
                    >
                      {stepExpanded ? (
                        <ChevronDown className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                      ) : (
                        <ChevronRight className="w-3.5 h-3.5 text-gray-400 shrink-0" />
                      )}
                      <span className="text-xs font-medium text-gray-500">Thought</span>
                    </button>
                    {stepExpanded && (
                      <div className="px-4 pb-3 pt-0 pl-8">
                        <div className="flex items-center gap-2 text-xs text-gray-600 bg-white rounded-lg border border-gray-200 px-3 py-2">
                          <span className="text-indigo-500">∞</span>
                          <span>{thought}</span>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
