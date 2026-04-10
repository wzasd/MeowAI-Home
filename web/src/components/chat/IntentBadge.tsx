/** Intent mode badge component */

interface IntentBadgeProps {
  mode: string | null;
}

const INTENT_STYLES: Record<
  string,
  { label: string; color: string; bg: string; darkColor: string; darkBg: string }
> = {
  ideate: {
    label: "头脑风暴",
    color: "text-purple-700",
    bg: "bg-purple-100",
    darkColor: "dark:text-purple-300",
    darkBg: "dark:bg-purple-900/30",
  },
  execute: {
    label: "执行模式",
    color: "text-blue-700",
    bg: "bg-blue-100",
    darkColor: "dark:text-blue-300",
    darkBg: "dark:bg-blue-900/30",
  },
  critique: {
    label: "审查模式",
    color: "text-amber-700",
    bg: "bg-amber-100",
    darkColor: "dark:text-amber-300",
    darkBg: "dark:bg-amber-900/30",
  },
};

export function IntentBadge({ mode }: IntentBadgeProps) {
  if (!mode) return null;

  const style = INTENT_STYLES[mode] || {
    label: mode,
    color: "text-gray-700",
    bg: "bg-gray-100",
    darkColor: "dark:text-gray-300",
    darkBg: "dark:bg-gray-800",
  };

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${style.bg} ${style.color} ${style.darkBg} ${style.darkColor}`}
    >
      {style.label}
    </span>
  );
}
