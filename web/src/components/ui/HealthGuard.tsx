/** Health protection modal - reminds users to take breaks */

import { useState, useEffect, useCallback } from "react";
import { X, Heart, Coffee, Moon } from "lucide-react";
type AlertLevel = "none" | "l1" | "l2" | "l3";

interface HealthMessage {
  title: string;
  message: string;
  icon: React.ReactNode;
  bgColor: string;
  textColor: string;
}

const HEALTH_MESSAGES: Record<Exclude<AlertLevel, "none">, HealthMessage> = {
  l1: {
    title: "休息提醒",
    message: "你已经连续使用一段时间了，起来活动一下吧~",
    icon: <Coffee size={32} />,
    bgColor: "bg-yellow-50 dark:bg-yellow-900/20",
    textColor: "text-yellow-700 dark:text-yellow-300",
  },
  l2: {
    title: "健康警告",
    message: "眼睛需要休息，建议远眺窗外或闭目养神几分钟。",
    icon: <Heart size={32} />,
    bgColor: "bg-orange-50 dark:bg-orange-900/20",
    textColor: "text-orange-700 dark:text-orange-300",
  },
  l3: {
    title: "强制休息",
    message: "为了你的健康，建议暂停使用，好好休息一下吧。",
    icon: <Moon size={32} />,
    bgColor: "bg-red-50 dark:bg-red-900/20",
    textColor: "text-red-700 dark:text-red-300",
  },
};

// Time thresholds in minutes
const THRESHOLDS = {
  l1: 30, // 30 minutes
  l2: 60, // 1 hour
  l3: 120, // 2 hours
};

export function HealthGuard() {
  const [level, setLevel] = useState<AlertLevel>("none");
  const [isDismissed, setIsDismissed] = useState(false);

  const checkUsageTime = useCallback(() => {
    const startTime = sessionStorage.getItem("meowai_start_time");
    if (!startTime) {
      sessionStorage.setItem("meowai_start_time", Date.now().toString());
      return;
    }

    const elapsed = (Date.now() - parseInt(startTime, 10)) / 1000 / 60; // in minutes

    if (elapsed >= THRESHOLDS.l3) {
      setLevel("l3");
    } else if (elapsed >= THRESHOLDS.l2) {
      setLevel("l2");
    } else if (elapsed >= THRESHOLDS.l1) {
      setLevel("l1");
    } else {
      setLevel("none");
    }
  }, []);

  useEffect(() => {
    // Check every minute
    const interval = setInterval(checkUsageTime, 60000);
    checkUsageTime(); // Initial check

    return () => clearInterval(interval);
  }, [checkUsageTime]);

  const handleDismiss = () => {
    setIsDismissed(true);
    // Reset after 5 minutes for L1/L2, L3 stays dismissed until page reload
    if (level !== "l3") {
      setTimeout(
        () => {
          setIsDismissed(false);
        },
        5 * 60 * 1000
      );
    }
  };

  const handleReset = () => {
    sessionStorage.setItem("meowai_start_time", Date.now().toString());
    setLevel("none");
    setIsDismissed(false);
  };

  if (level === "none" || isDismissed) return null;

  const health = HEALTH_MESSAGES[level];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className={`w-full max-w-sm rounded-2xl ${health.bgColor} p-6 shadow-2xl`}>
        <div className="mb-4 flex items-center justify-between">
          <div className={`${health.textColor}`}>{health.icon}</div>
          {level !== "l3" && (
            <button
              onClick={handleDismiss}
              className="rounded-full p-1 text-gray-400 hover:bg-black/5 hover:text-gray-600 dark:hover:bg-white/5 dark:hover:text-gray-300"
            >
              <X size={20} />
            </button>
          )}
        </div>

        <h3 className={`mb-2 text-lg font-bold ${health.textColor}`}>{health.title}</h3>
        <p className="mb-6 text-gray-600 dark:text-gray-300">{health.message}</p>

        <div className="flex gap-3">
          <button
            onClick={handleReset}
            className="flex-1 rounded-lg bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
          >
            我已休息
          </button>
          {level !== "l3" && (
            <button
              onClick={handleDismiss}
              className="flex-1 rounded-lg bg-blue-500 px-4 py-2 text-sm font-medium text-white hover:bg-blue-600"
            >
              稍后提醒
            </button>
          )}
        </div>

        <p className="mt-4 text-center text-xs text-gray-400">
          连续使用时长:{" "}
          {Math.floor(
            (Date.now() - parseInt(sessionStorage.getItem("meowai_start_time") || "0", 10)) /
              1000 /
              60
          )}{" "}
          分钟
        </p>
      </div>
    </div>
  );
}
