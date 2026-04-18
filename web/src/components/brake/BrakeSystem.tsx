/** Brake System - Emergency stop and safety controls */

import { useState } from "react";
import { AlertOctagon, ChevronDown, ChevronRight, Pause, Play, Shield } from "lucide-react";

interface BrakeStatus {
  isActive: boolean;
  triggeredAt?: string;
  reason?: string;
  canResume: boolean;
}

export function BrakeSystem() {
  const [status, setStatus] = useState<BrakeStatus>({
    isActive: false,
    canResume: true,
  });
  const [isExpanded, setIsExpanded] = useState(false);
  const [isArmed, setIsArmed] = useState(false);

  const triggerBrake = () => {
    setStatus({
      isActive: true,
      triggeredAt: new Date().toISOString(),
      reason: "用户手动触发",
      canResume: false,
    });
    setIsArmed(false);
    setIsExpanded(true);
    window.dispatchEvent(new CustomEvent("meowai:brake", { detail: { active: true } }));
  };

  const resume = () => {
    setStatus({
      isActive: false,
      canResume: true,
    });
    setIsArmed(false);
    window.dispatchEvent(new CustomEvent("meowai:brake", { detail: { active: false } }));
  };

  return (
    <div className="nest-card nest-r-lg border-[var(--border-strong)]/45 border bg-[linear-gradient(135deg,rgba(255,248,241,0.96),rgba(255,255,255,0.7))] p-3 dark:bg-[linear-gradient(135deg,rgba(48,32,20,0.45),rgba(255,255,255,0.04))]">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span
              className={`flex h-8 w-8 items-center justify-center rounded-2xl ${
                status.isActive
                  ? "bg-red-100 text-red-600 dark:bg-red-950/30 dark:text-red-300"
                  : "bg-amber-100 text-amber-700 dark:bg-amber-950/30 dark:text-amber-300"
              }`}
            >
              {status.isActive ? <AlertOctagon size={16} /> : <Shield size={16} />}
            </span>
            <div className="min-w-0">
              <div className="text-sm font-semibold text-[var(--text-strong)]">紧急刹车</div>
              <div className="text-[10px] text-[var(--text-faint)]">
                只在需要立即冻结自动流程时使用
              </div>
            </div>
          </div>

          <div className="mt-2 flex items-center gap-2 text-[10px]">
            <span
              className={`rounded-full px-2 py-0.5 font-medium ${
                status.isActive
                  ? "bg-red-100 text-red-700 dark:bg-red-950/30 dark:text-red-300"
                  : "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300"
              }`}
            >
              {status.isActive ? "已触发" : "待命"}
            </span>
            {status.triggeredAt && status.isActive && (
              <span className="text-[var(--text-faint)]">
                {new Date(status.triggeredAt).toLocaleTimeString()}
              </span>
            )}
          </div>
        </div>

        <button
          type="button"
          onClick={() => {
            setIsExpanded((current) => !current);
            if (isExpanded) setIsArmed(false);
          }}
          className="nest-button-ghost flex h-8 w-8 shrink-0 items-center justify-center rounded-full"
          aria-label={isExpanded ? "收起紧急刹车面板" : "展开紧急刹车面板"}
        >
          {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>
      </div>

      {isExpanded && (
        <div className="mt-3 border-t border-[var(--line)] pt-3">
          <p className="text-[11px] leading-5 text-[var(--text-soft)]">
            触发后会立即广播刹车事件，适合在自动流程异常、需要人工接管时使用。
          </p>

          {status.isActive ? (
            <>
              {status.reason && (
                <div className="mt-3 rounded-2xl border border-red-200/70 bg-red-50/80 px-3 py-2 text-[11px] text-red-700 dark:border-red-900/40 dark:bg-red-950/25 dark:text-red-300">
                  <span className="font-medium">原因</span>
                  <span className="ml-2">{status.reason}</span>
                </div>
              )}

              <div className="mt-3 flex justify-end">
                <button
                  onClick={resume}
                  className="nest-button-primary bg-emerald-600 px-3 py-1.5 text-xs hover:bg-emerald-700"
                >
                  <Play size={12} />
                  恢复运行
                </button>
              </div>
            </>
          ) : (
            <>
              {isArmed ? (
                <div className="mt-3 rounded-2xl border border-red-200/70 bg-red-50/80 px-3 py-2 dark:border-red-900/40 dark:bg-red-950/25">
                  <div className="text-[11px] font-medium text-red-700 dark:text-red-300">
                    确认触发刹车
                  </div>
                  <div className="mt-1 text-[11px] text-red-700/80 dark:text-red-300/80">
                    这会立即停止当前自动流程，直到你手动恢复。
                  </div>
                  <div className="mt-3 flex justify-end gap-2">
                    <button
                      onClick={() => setIsArmed(false)}
                      className="nest-button-secondary px-3 py-1.5 text-xs"
                    >
                      取消
                    </button>
                    <button
                      onClick={triggerBrake}
                      className="nest-button-primary bg-red-600 px-3 py-1.5 text-xs hover:bg-red-700"
                    >
                      <Pause size={12} />
                      立即刹车
                    </button>
                  </div>
                </div>
              ) : (
                <div className="mt-3 flex justify-end">
                  <button
                    onClick={() => setIsArmed(true)}
                    className="nest-button-secondary border-red-200/70 px-3 py-1.5 text-xs text-red-700 hover:bg-red-50 dark:border-red-900/40 dark:text-red-300 dark:hover:bg-red-950/20"
                  >
                    <Pause size={12} />
                    紧急刹车
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
