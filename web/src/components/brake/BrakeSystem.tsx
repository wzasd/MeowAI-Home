/** Brake System - Emergency stop and safety controls */

import { useState } from "react";
import { AlertOctagon, Shield, Play, Pause } from "lucide-react";

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
  const [showConfirm, setShowConfirm] = useState(false);

  const triggerBrake = () => {
    setStatus({
      isActive: true,
      triggeredAt: new Date().toISOString(),
      reason: "用户手动触发",
      canResume: false,
    });
    setShowConfirm(false);
    // Dispatch global event
    window.dispatchEvent(new CustomEvent("meowai:brake", { detail: { active: true } }));
  };

  const resume = () => {
    setStatus({
      isActive: false,
      canResume: true,
    });
    window.dispatchEvent(new CustomEvent("meowai:brake", { detail: { active: false } }));
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {status.isActive ? (
            <>
              <AlertOctagon size={18} className="animate-pulse text-red-500" />
              <span className="text-sm font-medium text-red-600">刹车已激活</span>
            </>
          ) : (
            <>
              <Shield size={18} className="text-green-500" />
              <span className="text-sm font-medium text-green-600">系统正常</span>
            </>
          )}
        </div>

        {status.isActive ? (
          <button
            onClick={resume}
            className="flex items-center gap-1 rounded bg-green-600 px-3 py-1.5 text-xs text-white hover:bg-green-700"
          >
            <Play size={12} />
            恢复运行
          </button>
        ) : (
          <button
            onClick={() => setShowConfirm(true)}
            className="flex items-center gap-1 rounded bg-red-600 px-3 py-1.5 text-xs text-white hover:bg-red-700"
          >
            <Pause size={12} />
            紧急刹车
          </button>
        )}
      </div>

      {status.isActive && status.reason && (
        <div className="mt-2 rounded bg-red-50 px-2 py-1.5 text-xs text-red-700 dark:bg-red-900/20">
          <span className="font-medium">原因:</span> {status.reason}
          {status.triggeredAt && (
            <span className="ml-2 text-red-500">
              {new Date(status.triggeredAt).toLocaleTimeString()}
            </span>
          )}
        </div>
      )}

      {/* Confirmation Dialog */}
      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-80 rounded-xl bg-white p-4 shadow-xl dark:bg-gray-800">
            <div className="flex items-center gap-2 text-red-600">
              <AlertOctagon size={20} />
              <h3 className="font-semibold">确认触发刹车?</h3>
            </div>
            <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
              这将立即停止所有 AI 操作。您可以在确认安全后恢复运行。
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={() => setShowConfirm(false)}
                className="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100"
              >
                取消
              </button>
              <button
                onClick={triggerBrake}
                className="rounded bg-red-600 px-3 py-1.5 text-sm text-white hover:bg-red-700"
              >
                确认刹车
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
