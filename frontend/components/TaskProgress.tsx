"use client";

import { useState, useEffect } from "react";
import {
  CheckCircle2,
  Circle,
  Loader2,
  ChevronRight,
  ChevronDown,
  Brain,
  ListChecks,
  Wrench,
  ArrowRight,
  ArrowDown,
  Sparkles,
  Clock,
  Zap,
} from "lucide-react";

export interface TaskStep {
  id: string;
  action: string;
  status: "pending" | "running" | "done";
  progress?: number;
  message?: string;
  tool_name?: string;
  params?: any;
  result?: any;
}

interface TaskProgressProps {
  steps: TaskStep[];
  agentThought?: string;
  stepThoughts?: Record<string, string>;
}

function ToolBadge({ name }: { name: string }) {
  const colorMap: Record<string, string> = {
    SearchTool: "bg-blue-50 text-blue-700 border-blue-200",
    DocEditTool: "bg-amber-50 text-amber-700 border-amber-200",
    SummarizeTool: "bg-violet-50 text-violet-700 border-violet-200",
    FilterTool: "bg-cyan-50 text-cyan-700 border-cyan-200",
    CitationTool: "bg-rose-50 text-rose-700 border-rose-200",
    MultiModalRAGTool: "bg-emerald-50 text-emerald-700 border-emerald-200",
    ProfileTool: "bg-orange-50 text-orange-700 border-orange-200",
  };
  const cls = colorMap[name] || "bg-gray-50 text-gray-600 border-gray-200";
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-semibold border ${cls}`}>
      <Wrench className="w-3 h-3" />
      {name}
    </span>
  );
}

function JsonBlock({ data, variant = "input" }: { data: any; variant?: "input" | "output" }) {
  const [collapsed, setCollapsed] = useState(true);

  let text: string;
  try {
    text = JSON.stringify(data, null, 2);
  } catch {
    text = String(data);
  }

  const lines = text.split("\n");
  const isLong = lines.length > 8;
  const displayText = collapsed ? lines.slice(0, 5).join("\n") + "\n  ..." : text;

  const isOutput = variant === "output";

  return (
    <div className="relative group">
      <div className={`text-[11px] font-semibold mb-1 flex items-center gap-1.5 ${isOutput ? "text-emerald-600" : "text-slate-500"}`}>
        {isOutput ? (
          <>
            <ArrowDown className="w-3 h-3" />
            <span>返回结果</span>
          </>
        ) : (
          <>
            <ArrowRight className="w-3 h-3" />
            <span>输入参数</span>
          </>
        )}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="ml-auto text-[10px] text-indigo-500 hover:text-indigo-700 font-medium"
        >
          {collapsed ? "展开" : "收起"}
        </button>
      </div>
      <pre
        className={`text-[11px] leading-[1.6] p-3 rounded-lg overflow-x-auto font-mono ${
          isOutput
            ? "bg-emerald-950/95 text-emerald-200 border border-emerald-900/50"
            : "bg-slate-900/95 text-slate-300 border border-slate-700/50"
        }`}
      >
        <code>{displayText}</code>
      </pre>
    </div>
  );
}

function StepStatusIcon({ status }: { status: "pending" | "running" | "done" }) {
  if (status === "done") {
    return (
      <div className="relative">
        <CheckCircle2 className="w-5 h-5 text-emerald-500" />
        <div className="absolute inset-0 rounded-full bg-emerald-400/20 animate-ping-once" />
      </div>
    );
  }
  if (status === "running") {
    return (
      <div className="relative flex items-center justify-center">
        <div className="absolute w-6 h-6 rounded-full bg-indigo-400/20 animate-pulse" />
        <Loader2 className="w-5 h-5 text-indigo-500 animate-spin" />
      </div>
    );
  }
  return <Circle className="w-5 h-5 text-slate-300" />;
}

export default function TaskProgress({ steps, agentThought = "", stepThoughts = {} }: TaskProgressProps) {
  const [expandedSteps, setExpandedSteps] = useState<Record<string, boolean>>({});
  const [thoughtVisible, setThoughtVisible] = useState(true);

  const doneCount = steps.filter((s) => s.status === "done").length;
  const allDone = doneCount === steps.length && steps.length > 0;
  const hasRunning = steps.some((s) => s.status === "running");
  const progressPercent = steps.length > 0 ? Math.round((doneCount / steps.length) * 100) : 0;

  useEffect(() => {
    const newExpanded: Record<string, boolean> = {};
    for (const step of steps) {
      if (step.status === "running" || step.status === "done") {
        if (expandedSteps[step.id] === undefined) {
          newExpanded[step.id] = true;
        }
      }
    }
    if (Object.keys(newExpanded).length > 0) {
      setExpandedSteps((prev) => ({ ...prev, ...newExpanded }));
    }
  }, [steps]);

  if (steps.length === 0) return null;

  const toggleStep = (id: string) => {
    setExpandedSteps((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="w-full max-w-[90%] animate-fade-in">
      {/* Thinking Section */}
      {agentThought && (
        <div className="mb-3">
          <button
            onClick={() => setThoughtVisible(!thoughtVisible)}
            className="flex items-center gap-2 text-xs font-semibold text-slate-500 hover:text-indigo-600 transition-colors mb-1.5 group"
          >
            <Brain className="w-3.5 h-3.5 text-indigo-400 group-hover:text-indigo-500" />
            <span>思考过程</span>
            {thoughtVisible ? (
              <ChevronDown className="w-3 h-3 text-slate-400" />
            ) : (
              <ChevronRight className="w-3 h-3 text-slate-400" />
            )}
          </button>
          {thoughtVisible && (
            <div className="ml-5 relative animate-slide-down">
              <div className="absolute left-0 top-0 bottom-0 w-[2px] bg-gradient-to-b from-indigo-300 to-purple-300 rounded-full" />
              <div className="pl-4 py-2">
                <p className="text-[13px] text-slate-600 leading-relaxed whitespace-pre-wrap">{agentThought}</p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Plan Card */}
      <div className="bg-white border border-slate-200/80 rounded-xl shadow-sm overflow-hidden">
        {/* Plan Header */}
        <div className="px-4 py-3 bg-gradient-to-r from-slate-50 to-white border-b border-slate-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className={`p-1 rounded-md ${allDone ? "bg-emerald-100" : hasRunning ? "bg-indigo-100" : "bg-slate-100"}`}>
                {allDone ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                ) : hasRunning ? (
                  <Zap className="w-4 h-4 text-indigo-600" />
                ) : (
                  <ListChecks className="w-4 h-4 text-slate-500" />
                )}
              </div>
              <span className="text-sm font-bold text-slate-800">执行计划</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1.5">
                <div className="w-24 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ease-out ${
                      allDone ? "bg-emerald-500" : "bg-indigo-500"
                    }`}
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
                <span className="text-[11px] font-semibold text-slate-500 tabular-nums">
                  {doneCount}/{steps.length}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Steps Timeline */}
        <div className="px-4 py-3">
          {steps.map((step, index) => {
            const isLast = index === steps.length - 1;
            const thought = stepThoughts[step.id];
            const isExpanded = expandedSteps[step.id] ?? false;
            const hasDetails = step.tool_name && (step.params || step.result);
            const hasThought = !!thought && step.status === "done";

            return (
              <div key={step.id} className="relative">
                {/* Timeline connector */}
                {!isLast && (
                  <div
                    className={`absolute left-[9px] top-[26px] w-[2px] bottom-0 ${
                      step.status === "done" ? "bg-emerald-200" : "bg-slate-200"
                    }`}
                  />
                )}

                <div className="relative flex gap-3 pb-4">
                  {/* Status Icon */}
                  <div className="shrink-0 z-10 bg-white">
                    <StepStatusIcon status={step.status} />
                  </div>

                  {/* Step Content */}
                  <div className="flex-1 min-w-0 -mt-0.5">
                    {/* Step Header */}
                    <div
                      className={`flex items-start gap-2 cursor-pointer select-none group ${
                        hasDetails || hasThought ? "" : "cursor-default"
                      }`}
                      onClick={() => (hasDetails || hasThought) && toggleStep(step.id)}
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span
                            className={`text-[13px] font-semibold leading-snug ${
                              step.status === "done"
                                ? "text-slate-700"
                                : step.status === "running"
                                ? "text-indigo-700"
                                : "text-slate-400"
                            }`}
                          >
                            {step.action}
                          </span>
                          {step.tool_name && <ToolBadge name={step.tool_name} />}
                        </div>

                        {/* Running indicator */}
                        {step.status === "running" && (
                          <div className="mt-2">
                            {step.progress !== undefined ? (
                              <div className="flex items-center gap-2">
                                <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                  <div
                                    className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full transition-all duration-300"
                                    style={{ width: `${step.progress * 100}%` }}
                                  />
                                </div>
                                <span className="text-[10px] text-slate-400 tabular-nums">
                                  {Math.round(step.progress * 100)}%
                                </span>
                              </div>
                            ) : (
                              <div className="flex items-center gap-1.5 text-[11px] text-indigo-500">
                                <Clock className="w-3 h-3" />
                                <span>{step.message || "执行中..."}</span>
                              </div>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Expand Chevron */}
                      {(hasDetails || hasThought) && (
                        <div className="mt-0.5 shrink-0 p-0.5 rounded hover:bg-slate-100 transition-colors">
                          {isExpanded ? (
                            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                          ) : (
                            <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                          )}
                        </div>
                      )}
                    </div>

                    {/* Expanded Detail */}
                    {isExpanded && (hasDetails || hasThought) && (
                      <div className="mt-2.5 space-y-2.5 animate-slide-down">
                        {/* Tool call details */}
                        {step.params && <JsonBlock data={step.params} variant="input" />}
                        {step.result && <JsonBlock data={step.result} variant="output" />}

                        {/* Step thought */}
                        {hasThought && (
                          <div className="flex items-start gap-2 p-2.5 rounded-lg bg-gradient-to-r from-indigo-50/80 to-purple-50/50 border border-indigo-100/80">
                            <Sparkles className="w-3.5 h-3.5 text-indigo-400 mt-0.5 shrink-0" />
                            <p className="text-[12px] text-slate-600 leading-relaxed">{thought}</p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
