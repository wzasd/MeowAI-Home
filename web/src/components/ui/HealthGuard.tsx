/** Health protection modal - reminds users to take breaks */

import { useState, useEffect, useCallback } from "react";
import { X, Heart, Coffee, Moon } from "lucide-react";
import {
  getAlertLevel,
  getSnoozeUntil,
  HEALTH_SNOOZE_UNTIL_KEY,
  HEALTH_START_KEY,
  isHealthGuardSnoozed,
  type AlertLevel,
} from "./healthGuardModel";

interface HealthMessage {
  title: string;
  message: string;
  icon: React.ReactNode;
  bgColor: string;
  textColor: string;
  ringColor: string;
}

const HEALTH_MESSAGES: Record<Exclude<AlertLevel, "none">, HealthMessage> = {
  l1: {
    title: "休息提醒",
    message: "你已经连续使用一段时间了，起来活动一下吧~",
    icon: <Coffee size={32} />,
    bgColor: "bg-yellow-50 dark:bg-yellow-900/20",
    textColor: "text-yellow-700 dark:text-yellow-300",
    ringColor: "ring-yellow-200/70 dark:ring-yellow-800/40",
  },
  l2: {
    title: "健康警告",
    message: "眼睛需要休息，建议远眺窗外或闭目养神几分钟。",
    icon: <Heart size={32} />,
    bgColor: "bg-orange-50 dark:bg-orange-900/20",
    textColor: "text-orange-700 dark:text-orange-300",
    ringColor: "ring-orange-200/70 dark:ring-orange-800/40",
  },
  l3: {
    title: "强制休息",
    message: "为了你的健康，建议暂停使用，好好休息一下吧。",
    icon: <Moon size={32} />,
    bgColor: "bg-red-50 dark:bg-red-900/20",
    textColor: "text-red-700 dark:text-red-300",
    ringColor: "ring-red-200/70 dark:ring-red-800/40",
  },
};

export function HealthGuard() {
  const [level, setLevel] = useState<AlertLevel>("none");
  const [elapsedMinutes, setElapsedMinutes] = useState(0);

  const checkUsageTime = useCallback(() => {
    const now = Date.now();
    const startTime = sessionStorage.getItem(HEALTH_START_KEY);
    if (!startTime) {
      sessionStorage.setItem(HEALTH_START_KEY, now.toString());
      setLevel("none");
      setElapsedMinutes(0);
      return;
    }

    const startTimeMs = parseInt(startTime, 10);
    setElapsedMinutes(Math.max(0, Math.floor((now - startTimeMs) / 1000 / 60)));

    const snoozeUntil = parseInt(sessionStorage.getItem(HEALTH_SNOOZE_UNTIL_KEY) || "", 10);
    if (isHealthGuardSnoozed(snoozeUntil, now)) {
      setLevel("none");
      return;
    }

    setLevel(getAlertLevel(startTimeMs, now));
  }, []);

  useEffect(() => {
    // Check every minute
    const interval = setInterval(checkUsageTime, 60000);
    const initialCheck = window.setTimeout(checkUsageTime, 0);

    return () => {
      clearInterval(interval);
      window.clearTimeout(initialCheck);
    };
  }, [checkUsageTime]);

  const handleDismiss = () => {
    if (level === "none") return;
    sessionStorage.setItem(HEALTH_SNOOZE_UNTIL_KEY, getSnoozeUntil(level, Date.now()).toString());
    setLevel("none");
  };

  const handleReset = () => {
    sessionStorage.setItem(HEALTH_START_KEY, Date.now().toString());
    sessionStorage.removeItem(HEALTH_SNOOZE_UNTIL_KEY);
    setLevel("none");
  };

  if (level === "none") return null;

  const health = HEALTH_MESSAGES[level];

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-40 flex justify-end p-4">
      <div
        className={`pointer-events-auto w-full max-w-sm rounded-2xl border border-[var(--border)] ${health.bgColor} p-5 shadow-[0_24px_50px_-24px_rgba(15,23,42,0.55)] ring-1 ${health.ringColor} backdrop-blur`}
      >
        <div className="mb-4 flex items-center justify-between gap-3">
          <div className={`${health.textColor}`}>{health.icon}</div>
          <button
            onClick={handleDismiss}
            className="rounded-full p-1 text-gray-400 transition-colors hover:bg-black/5 hover:text-gray-600 dark:hover:bg-white/5 dark:hover:text-gray-300"
            aria-label="关闭健康提醒"
          >
            <X size={20} />
          </button>
        </div>

        <h3 className={`mb-2 text-lg font-bold ${health.textColor}`}>{health.title}</h3>
        <p className="mb-5 text-sm leading-6 text-gray-600 dark:text-gray-300">{health.message}</p>

        <div className="flex gap-3">
          <button
            onClick={handleReset}
            className="flex-1 rounded-lg bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
          >
            我已休息
          </button>
          <button
            onClick={handleDismiss}
            className="flex-1 rounded-lg bg-blue-500 px-4 py-2 text-sm font-medium text-white hover:bg-blue-600"
          >
            稍后提醒
          </button>
        </div>

        <p className="mt-4 text-center text-xs text-gray-400">
          连续使用时长: {elapsedMinutes} 分钟
        </p>
      </div>
    </div>
  );
}
