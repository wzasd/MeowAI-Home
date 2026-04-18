export type AlertLevel = "none" | "l1" | "l2" | "l3";

export const HEALTH_START_KEY = "meowai_start_time";
export const HEALTH_SNOOZE_UNTIL_KEY = "meowai_health_snooze_until";

const THRESHOLD_MINUTES = {
  l1: 30,
  l2: 60,
  l3: 120,
} as const;

const SNOOZE_MINUTES = {
  l1: 5,
  l2: 5,
  l3: 15,
} as const;

export function getAlertLevel(startTimeMs: number | null, nowMs: number): AlertLevel {
  if (!startTimeMs || Number.isNaN(startTimeMs)) {
    return "none";
  }

  const elapsedMinutes = (nowMs - startTimeMs) / 1000 / 60;

  if (elapsedMinutes >= THRESHOLD_MINUTES.l3) {
    return "l3";
  }
  if (elapsedMinutes >= THRESHOLD_MINUTES.l2) {
    return "l2";
  }
  if (elapsedMinutes >= THRESHOLD_MINUTES.l1) {
    return "l1";
  }
  return "none";
}

export function isHealthGuardSnoozed(snoozeUntilMs: number | null, nowMs: number): boolean {
  if (!snoozeUntilMs || Number.isNaN(snoozeUntilMs)) {
    return false;
  }
  return snoozeUntilMs > nowMs;
}

export function getSnoozeUntil(level: Exclude<AlertLevel, "none">, nowMs: number): number {
  return nowMs + SNOOZE_MINUTES[level] * 60 * 1000;
}

