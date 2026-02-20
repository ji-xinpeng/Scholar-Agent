"use client";

import { useState } from "react";
import {
  CheckCircle2,
  Circle,
  Loader2,
  ChevronDown,
  ChevronRight,
  Brain,
  Wrench,
  ArrowRight,
  ArrowDown,
  Sparkles,
  Clock,
  Zap,
  MessageSquare,
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

export type AgentTimelineEvent =
  | { type: "thought"; content: string }
  | { type: "step_start"; stepId: string; toolName: string; action: string }
  | { type: "step_done"; stepId: string; result: string };

interface TaskProgressProps {
  steps: TaskStep[];
  stepThoughts?: Record<string, string>;
  timeline?: AgentTimelineEvent[];
  agentThought?: string;
}

/* ── Utility Components ── */

const toolColors: Record<string, string> = {
  SearchTool: "text-blue-600 bg-blue-50",
  PaperDownloadTool: "text-sky-600 bg-sky-50",
  DocEditTool: "text-amber-600 bg-amber-50",
  SummarizeTool: "text-violet-600 bg-violet-50",
  FilterTool: "text-cyan-600 bg-cyan-50",
  CitationTool: "text-rose-600 bg-rose-50",
  MultiModalRAGTool: "text-emerald-600 bg-emerald-50",
  ProfileTool: "text-orange-600 bg-orange-50",
  LLMCallTool: "text-indigo-600 bg-indigo-50",
};

function ToolTag({ name }: { name: string }) {
  const cls = toolColors[name] || "text-slate-500 bg-slate-50";
  return (
    <span className={`inline-flex items-center gap-0.5 px-1.5 py-px rounded text-[10px] font-medium ${cls}`}>
      <Wrench className="w-2.5 h-2.5" />
      {name}
    </span>
  );
}

function DataBlock({ data, label, variant }: { data: any; label: string; variant: "in" | "out" }) {
  const [open, setOpen] = useState(false);
  let text: string;
  try { text = JSON.stringify(data, null, 2); } catch { text = String(data); }
  const lines = text.split("\n");
  const preview = lines.slice(0, 4).join("\n") + (lines.length > 4 ? "\n..." : "");
  const isOut = variant === "out";

  return (
    <div className="mt-1.5">
      <button onClick={() => setOpen(!open)} className={`text-[10px] font-medium flex items-center gap-1 ${isOut ? "text-emerald-500" : "text-slate-400"} hover:underline`}>
        {isOut ? <ArrowDown className="w-2.5 h-2.5" /> : <ArrowRight className="w-2.5 h-2.5" />}
        {label}
        <span className="text-slate-300 ml-1">{open ? "收起" : "查看"}</span>
      </button>
      {open && (
        <pre className={`mt-1 text-[10px] leading-relaxed p-2 rounded-lg overflow-x-auto font-mono ${isOut ? "bg-emerald-950/90 text-emerald-200" : "bg-slate-800 text-slate-300"}`}>
          <code>{text}</code>
        </pre>
      )}
      {!open && lines.length > 0 && (
        <pre className={`mt-1 text-[10px] leading-relaxed p-2 rounded-lg overflow-x-auto font-mono max-h-16 ${isOut ? "bg-emerald-950/90 text-emerald-200/70" : "bg-slate-800 text-slate-300/70"}`}>
          <code>{preview}</code>
        </pre>
      )}
    </div>
  );
}

/* ── Step Row ── */

function StepRow({ step, thought }: { step: TaskStep; thought?: string }) {
  const [expanded, setExpanded] = useState(false);
  const hasDetail = step.params || step.result;

  return (
    <div className="flex gap-2.5 group">
      {/* Status dot */}
      <div className="flex flex-col items-center pt-1 shrink-0">
        {step.status === "done" ? (
          <CheckCircle2 className="w-4 h-4 text-emerald-500" />
        ) : step.status === "running" ? (
          <Loader2 className="w-4 h-4 text-violet-500 animate-spin" />
        ) : (
          <Circle className="w-4 h-4 text-slate-300" />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 pb-2.5">
        <div
          className={`flex items-center gap-1.5 flex-wrap ${hasDetail ? "cursor-pointer" : ""}`}
          onClick={() => hasDetail && setExpanded(!expanded)}
        >
          <span className={`text-[12px] font-medium ${
            step.status === "done" ? "text-slate-700" : step.status === "running" ? "text-violet-700" : "text-slate-400"
          }`}>
            {step.action}
          </span>
          {step.tool_name && <ToolTag name={step.tool_name} />}
          {hasDetail && (
            <span className="text-slate-300 ml-auto shrink-0">
              {expanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
            </span>
          )}
        </div>

        {/* Running indicator */}
        {step.status === "running" && (
          <div className="mt-1 flex items-center gap-1.5 text-[10px] text-violet-500">
            <Clock className="w-2.5 h-2.5" />
            <span>{step.message || "执行中..."}</span>
            {step.progress !== undefined && step.progress > 0 && (
              <div className="flex items-center gap-1.5 ml-2">
                <div className="w-16 h-1 bg-slate-100 rounded-full overflow-hidden">
                  <div className="h-full bg-violet-500 rounded-full transition-all" style={{ width: `${step.progress * 100}%` }} />
                </div>
                <span className="tabular-nums">{Math.round(step.progress * 100)}%</span>
              </div>
            )}
          </div>
        )}

        {/* Result summary */}
        {step.status === "done" && thought && !expanded && (
          <div className="mt-0.5 text-[11px] text-slate-400 truncate">{thought}</div>
        )}

        {/* Expanded detail */}
        {expanded && (
          <div className="animate-slide-down">
            {step.params && <DataBlock data={step.params} label="输入参数" variant="in" />}
            {step.result && <DataBlock data={step.result} label="返回结果" variant="out" />}
            {thought && (
              <div className="mt-1.5 text-[11px] text-slate-500 flex items-start gap-1.5">
                <Sparkles className="w-3 h-3 text-violet-400 shrink-0 mt-px" />
                <span>{thought}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Main Component ── */

export default function TaskProgress({ steps, stepThoughts = {}, timeline = [], agentThought = "" }: TaskProgressProps) {
  const [expanded, setExpanded] = useState(true);

  const thoughts = timeline.filter((e) => e.type === "thought").map((e) => (e as { type: "thought"; content: string }).content);
  const latestThought = thoughts.length > 0 ? thoughts[thoughts.length - 1] : agentThought;
  const hasContent = latestThought || steps.length > 0;

  if (!hasContent) return null;

  const doneCount = steps.filter((s) => s.status === "done").length;
  const allDone = steps.length > 0 && doneCount === steps.length && !steps.some((s) => s.status === "running");
  const hasRunning = steps.some((s) => s.status === "running");
  const currentRunning = steps.find((s) => s.status === "running");

  // Header status line
  let statusText: string;
  let StatusIcon: React.ReactNode;
  if (allDone) {
    statusText = `已完成 ${doneCount} 个步骤`;
    StatusIcon = <CheckCircle2 className="w-4 h-4 text-emerald-500" />;
  } else if (hasRunning && currentRunning) {
    statusText = currentRunning.action;
    StatusIcon = <Loader2 className="w-4 h-4 text-violet-500 animate-spin" />;
  } else if (steps.length > 0) {
    statusText = `${doneCount}/${steps.length} 步骤`;
    StatusIcon = <Zap className="w-4 h-4 text-violet-500" />;
  } else {
    statusText = "正在分析...";
    StatusIcon = <Brain className="w-4 h-4 text-violet-500 animate-pulse" />;
  }

  return (
    <div className="w-full max-w-[90%] animate-fade-in">
      <div className={`rounded-2xl border overflow-hidden transition-colors ${
        allDone ? "border-emerald-200/60 bg-white" : "border-violet-200/50 bg-white"
      }`}>

        {/* ── Header ── */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center gap-2.5 px-4 py-2.5 hover:bg-slate-50/50 transition-colors"
        >
          {StatusIcon}
          <span className="text-[13px] font-semibold text-slate-700 truncate flex-1 text-left">{statusText}</span>
          {steps.length > 0 && (
            <span className={`text-[11px] font-bold tabular-nums px-2 py-0.5 rounded-full ${
              allDone ? "bg-emerald-100 text-emerald-700" : "bg-violet-100 text-violet-700"
            }`}>
              {doneCount}/{steps.length}
            </span>
          )}
          {expanded ? <ChevronDown className="w-4 h-4 text-slate-400 shrink-0" /> : <ChevronRight className="w-4 h-4 text-slate-400 shrink-0" />}
        </button>

        {/* ── Body ── */}
        {expanded && (
          <div className="px-4 pb-3 animate-slide-down">
            {/* Progress bar */}
            {steps.length > 0 && (
              <div className="mb-3 h-1 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-700 ease-out ${allDone ? "bg-emerald-500" : "bg-gradient-to-r from-violet-500 to-indigo-500"}`}
                  style={{ width: `${steps.length > 0 ? (doneCount / steps.length) * 100 : 0}%` }}
                />
              </div>
            )}

            {/* Timeline: interleave thoughts and steps */}
            {(() => {
              const items: React.ReactNode[] = [];
              let thoughtIdx = 0;
              let stepIdx = 0;
              const thoughtEvents = timeline.filter((e) => e.type === "thought");
              const stepStartEvents = timeline.filter((e) => e.type === "step_start");

              // Build ordered items from timeline
              for (const event of timeline) {
                if (event.type === "thought") {
                  items.push(
                    <div key={`t-${thoughtIdx}`} className="flex items-start gap-2 py-1.5">
                      <MessageSquare className="w-3.5 h-3.5 text-violet-400 shrink-0 mt-0.5" />
                      <p className="text-[12px] text-slate-500 leading-relaxed whitespace-pre-wrap">{event.content}</p>
                    </div>
                  );
                  thoughtIdx++;
                }
                if (event.type === "step_start") {
                  const step = steps.find((s) => s.id === event.stepId);
                  if (step) {
                    items.push(
                      <StepRow key={`s-${step.id}`} step={step} thought={stepThoughts[step.id]} />
                    );
                  }
                  stepIdx++;
                }
              }

              // Show any steps not yet in timeline (pending)
              const timelineStepIds = new Set(stepStartEvents.map((e) => (e as { type: "step_start"; stepId: string }).stepId));
              for (const step of steps) {
                if (!timelineStepIds.has(step.id)) {
                  items.push(
                    <StepRow key={`s-${step.id}`} step={step} thought={stepThoughts[step.id]} />
                  );
                }
              }

              // If no timeline but have thoughts, show latest thought
              if (timeline.length === 0 && latestThought) {
                items.unshift(
                  <div key="t-fallback" className="flex items-start gap-2 py-1.5">
                    <MessageSquare className="w-3.5 h-3.5 text-violet-400 shrink-0 mt-0.5" />
                    <p className="text-[12px] text-slate-500 leading-relaxed whitespace-pre-wrap">{latestThought}</p>
                  </div>
                );
              }

              return items;
            })()}
          </div>
        )}
      </div>
    </div>
  );
}
