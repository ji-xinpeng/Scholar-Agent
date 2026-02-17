"use client";

import { CheckCircle2, Circle, Loader2 } from "lucide-react";

export interface TaskStep {
  id: string;
  action: string;
  status: "pending" | "running" | "done";
  progress?: number;
  message?: string;
}

interface TaskProgressProps {
  steps: TaskStep[];
}

export default function TaskProgress({ steps }: TaskProgressProps) {
  if (steps.length === 0) return null;

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm max-w-[75%]">
      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">研究计划</div>
      <div className="space-y-2.5">
        {steps.map((step) => (
          <div key={step.id} className="flex items-start gap-2.5">
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
                    ? "text-gray-500 line-through"
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
                  {step.message && <div className="text-xs text-gray-400 mt-1">{step.message}</div>}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
