import type { ReactNode } from "react";

import type { SettingsSummaryCardModel, SettingsSummaryTone } from "./settingsSummaryModels";

interface SettingsSectionCardProps {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
}

const SUMMARY_TONES: Record<SettingsSummaryTone, string> = {
  neutral: "border-[var(--border)] bg-white/70 text-[var(--text-strong)] dark:bg-white/[0.04]",
  accent:
    "border-[rgba(183,103,37,0.18)] bg-[rgba(183,103,37,0.08)] text-[var(--accent-deep)] dark:bg-[rgba(230,162,93,0.12)]",
  success:
    "border-[rgba(47,116,103,0.18)] bg-[rgba(47,116,103,0.08)] text-[var(--moss)] dark:bg-[rgba(121,192,173,0.12)]",
  attention:
    "border-[rgba(141,104,68,0.18)] bg-[rgba(141,104,68,0.08)] text-[var(--text-strong)] dark:bg-[rgba(234,203,168,0.08)]",
};

export function SettingsSummaryGrid({ items }: { items: SettingsSummaryCardModel[] }) {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      {items.map((item) => (
        <div
          key={item.id}
          className={`nest-r-xl border px-4 py-4 shadow-[0_18px_40px_-28px_rgba(15,23,42,0.45)] ${SUMMARY_TONES[item.tone]}`}
        >
          <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[var(--text-faint)]">
            {item.label}
          </div>
          <div className="mt-3 text-[1.9rem] font-semibold leading-none">{item.value}</div>
          <p className="mt-3 text-sm leading-6 text-[var(--text-soft)]">{item.detail}</p>
        </div>
      ))}
    </div>
  );
}

export function SettingsSectionCard({
  eyebrow,
  title,
  description,
  actions,
  children,
}: SettingsSectionCardProps) {
  return (
    <section className="nest-panel nest-r-xl px-5 py-5 lg:px-6">
      <div className="flex flex-col gap-4 border-b border-[var(--line)] pb-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 max-w-3xl">
          {eyebrow && <div className="nest-kicker">{eyebrow}</div>}
          <h3 className="mt-2 text-lg font-semibold text-[var(--text-strong)]">{title}</h3>
          {description && (
            <p className="mt-2 text-sm leading-7 text-[var(--text-soft)]">{description}</p>
          )}
        </div>
        {actions && (
          <div className="flex shrink-0 flex-wrap items-center gap-2 lg:justify-end">{actions}</div>
        )}
      </div>
      <div className="pt-4">{children}</div>
    </section>
  );
}
