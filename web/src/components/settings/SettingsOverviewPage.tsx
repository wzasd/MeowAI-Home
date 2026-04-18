import { Bot, CalendarClock, ShieldCheck, Telescope } from "lucide-react";

import {
  buildSettingsOverviewCards,
  type SettingsGroupId,
  type SettingsPageId,
} from "./settingsRegistry";

interface SettingsOverviewPageProps {
  onSelectPage: (pageId: SettingsPageId) => void;
}

const GROUP_ICONS: Record<SettingsGroupId, typeof Bot> = {
  identity: Bot,
  runtime: ShieldCheck,
  automation: CalendarClock,
  observability: Telescope,
};

export function SettingsOverviewPage({ onSelectPage }: SettingsOverviewPageProps) {
  const cards = buildSettingsOverviewCards();

  return (
    <div className="space-y-4">
      <div className="grid gap-4 xl:grid-cols-2">
        {cards.map((card) => {
          const Icon = GROUP_ICONS[card.groupId];
          return (
            <button
              key={card.groupId}
              type="button"
              onClick={() => onSelectPage(card.targetPageId)}
              className="nest-panel nest-r-xl group flex flex-col gap-4 p-5 text-left transition-transform duration-200 hover:-translate-y-0.5 hover:border-[var(--border-strong)]"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-[var(--accent-soft)] text-[var(--accent-deep)] dark:text-[var(--accent)]">
                    <Icon size={18} />
                  </div>
                  <div>
                    <div className="nest-kicker">设置分组</div>
                    <h3 className="mt-1 text-base font-semibold text-[var(--text-strong)]">
                      {card.title}
                    </h3>
                  </div>
                </div>
                <span className="inline-flex items-center rounded-full border border-[var(--border)] bg-white/55 px-2.5 py-1 text-[11px] font-medium text-[var(--text-soft)] dark:bg-white/10">
                  {card.pageCount} 项
                </span>
              </div>

              <p className="text-sm leading-7 text-[var(--text-soft)]">{card.description}</p>

              <div className="flex flex-wrap gap-2">
                {card.pageLabels.map((pageLabel) => (
                  <span
                    key={pageLabel}
                    className="inline-flex items-center rounded-full border border-[var(--border)] bg-white/45 px-2.5 py-1 text-[11px] text-[var(--text-soft)] dark:bg-white/10"
                  >
                    {pageLabel}
                  </span>
                ))}
              </div>

              <div className="mt-auto flex items-center justify-between gap-3 pt-1">
                {card.flagLabel ? (
                  <span className="inline-flex items-center rounded-full border border-[rgba(141,104,68,0.18)] bg-[rgba(141,104,68,0.08)] px-2.5 py-1 text-[11px] font-medium text-[var(--text-soft)] dark:bg-[rgba(234,203,168,0.08)]">
                    {card.flagLabel}
                  </span>
                ) : (
                  <span className="text-[11px] text-[var(--text-faint)]">
                    当前阶段先用静态入口卡收口 IA
                  </span>
                )}
                <span className="text-xs font-medium text-[var(--accent-deep)] transition-transform duration-200 group-hover:translate-x-0.5 dark:text-[var(--accent)]">
                  打开分组
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
