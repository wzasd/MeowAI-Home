import type { ReactNode } from "react";

import type { SettingsPageStatus, SettingsSaveMode } from "./settingsRegistry";

interface SettingsPageHeroProps {
  eyebrow: string;
  title: string;
  description: string;
  saveMode: SettingsSaveMode;
  status?: SettingsPageStatus;
  actions?: ReactNode;
}

const SAVE_MODE_LABELS: Record<SettingsSaveMode, string> = {
  navigate: "从总览进入对应页面",
  auto: "修改后自动保存",
  manual: "编辑完成后点击保存",
  mixed: "即时执行 + 局部操作",
  readonly: "只读观察页",
};

const SAVE_MODE_TONES: Record<SettingsSaveMode, string> = {
  navigate: "border-[var(--border)] bg-white/55 text-[var(--text-soft)] dark:bg-white/10",
  auto: "border-[rgba(47,116,103,0.18)] bg-[rgba(47,116,103,0.08)] text-[var(--moss)] dark:bg-[rgba(121,192,173,0.12)]",
  manual:
    "border-[rgba(183,103,37,0.18)] bg-[rgba(183,103,37,0.08)] text-[var(--accent-deep)] dark:bg-[rgba(230,162,93,0.14)]",
  mixed:
    "border-[rgba(141,104,68,0.18)] bg-[rgba(141,104,68,0.08)] text-[var(--text-soft)] dark:bg-[rgba(234,203,168,0.08)]",
  readonly:
    "border-[rgba(93,118,141,0.18)] bg-[rgba(93,118,141,0.08)] text-[var(--text-soft)] dark:bg-[rgba(147,163,184,0.12)]",
};

export function SettingsPageHero({
  eyebrow,
  title,
  description,
  saveMode,
  status,
  actions,
}: SettingsPageHeroProps) {
  return (
    <div className="nest-panel nest-r-xl px-5 py-5 lg:px-6">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div className="min-w-0 max-w-3xl">
          <div className="flex flex-wrap items-center gap-2">
            <span className="nest-kicker">{eyebrow}</span>
            <span
              className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-medium ${
                SAVE_MODE_TONES[saveMode]
              }`}
            >
              {SAVE_MODE_LABELS[saveMode]}
            </span>
            {status === "migrating" && (
              <span className="inline-flex items-center rounded-full border border-[rgba(141,104,68,0.18)] bg-[rgba(141,104,68,0.08)] px-2.5 py-1 text-[11px] font-medium text-[var(--text-soft)] dark:bg-[rgba(234,203,168,0.08)]">
                迁出中
              </span>
            )}
          </div>
          <h2 className="nest-title mt-3 text-[1.85rem] font-semibold leading-tight text-[var(--text-strong)]">
            {title}
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-7 text-[var(--text-soft)]">{description}</p>
        </div>
        {actions && (
          <div className="flex flex-wrap items-center gap-2 xl:justify-end">{actions}</div>
        )}
      </div>
    </div>
  );
}
