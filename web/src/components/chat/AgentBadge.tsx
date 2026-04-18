import { CAT_INFO } from "../../types";

interface AgentBadgeProps {
  catId: string;
}

export function AgentBadge({ catId }: AgentBadgeProps) {
  const info = CAT_INFO[catId] || { name: catId, emoji: "🐾", color: "gray" };
  const colorClasses: Record<string, string> = {
    orange: "border-orange-200/70 bg-[linear-gradient(135deg,#fff1df,#ffd1a7)] text-orange-700 shadow-[0_10px_24px_rgba(230,155,88,0.22)] dark:border-orange-300/15 dark:bg-[linear-gradient(135deg,rgba(230,162,93,0.22),rgba(230,162,93,0.08))] dark:text-orange-200",
    purple: "border-purple-200/70 bg-[linear-gradient(135deg,#f8ebff,#e1c7ff)] text-purple-700 shadow-[0_10px_24px_rgba(158,112,213,0.18)] dark:border-purple-300/15 dark:bg-[linear-gradient(135deg,rgba(171,132,221,0.22),rgba(171,132,221,0.08))] dark:text-purple-200",
    pink: "border-pink-200/70 bg-[linear-gradient(135deg,#fff0f6,#ffcfe3)] text-pink-700 shadow-[0_10px_24px_rgba(224,121,166,0.18)] dark:border-pink-300/15 dark:bg-[linear-gradient(135deg,rgba(224,121,166,0.22),rgba(224,121,166,0.08))] dark:text-pink-200",
    gray: "border-[var(--border)] bg-[rgba(255,250,244,0.8)] text-[var(--text-soft)] shadow-[0_10px_24px_rgba(73,46,22,0.12)] dark:bg-white/5 dark:text-[var(--text-soft)]",
  };

  return (
    <div className="mr-3 shrink-0 self-end">
      <div
        className={`flex h-10 w-10 items-center justify-center nest-r-md border text-sm font-medium ${
          colorClasses[info.color] || colorClasses.gray
        }`}
        title={info.name}
      >
        {info.emoji}
      </div>
    </div>
  );
}
