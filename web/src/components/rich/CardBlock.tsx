import type { CardBlock } from "../../types/rich";
import { Info, CheckCircle2, AlertTriangle, XCircle } from "lucide-react";

const VARIANT_STYLES = {
  info: {
    border: "border-blue-200 dark:border-blue-800",
    bg: "bg-blue-50 dark:bg-blue-900/20",
    icon: Info,
    iconColor: "text-blue-500",
    title: "text-blue-800 dark:text-blue-300",
  },
  success: {
    border: "border-green-200 dark:border-green-800",
    bg: "bg-green-50 dark:bg-green-900/20",
    icon: CheckCircle2,
    iconColor: "text-green-500",
    title: "text-green-800 dark:text-green-300",
  },
  warning: {
    border: "border-amber-200 dark:border-amber-800",
    bg: "bg-amber-50 dark:bg-amber-900/20",
    icon: AlertTriangle,
    iconColor: "text-amber-500",
    title: "text-amber-800 dark:text-amber-300",
  },
  danger: {
    border: "border-red-200 dark:border-red-800",
    bg: "bg-red-50 dark:bg-red-900/20",
    icon: XCircle,
    iconColor: "text-red-500",
    title: "text-red-800 dark:text-red-300",
  },
};

export function CardBlockView({ block }: { block: CardBlock }) {
  const v = VARIANT_STYLES[block.variant] ?? VARIANT_STYLES.info;
  const Icon = v.icon;

  return (
    <div className={`rounded-lg border ${v.border} ${v.bg} p-4`}>
      {block.title && (
        <div className="mb-2 flex items-center gap-2">
          <Icon size={16} className={v.iconColor} />
          <h4 className={`text-sm font-semibold ${v.title}`}>{block.title}</h4>
        </div>
      )}
      {block.fields && block.fields.length > 0 && (
        <dl className="space-y-1 text-sm">
          {block.fields.map((f, i) => (
            <div key={i} className="flex gap-2">
              <dt className="shrink-0 text-gray-500 dark:text-gray-400">{f.label}:</dt>
              <dd className="text-gray-800 dark:text-gray-200">{f.value}</dd>
            </div>
          ))}
        </dl>
      )}
      {block.actions && block.actions.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {block.actions.map((a, i) => (
            <button
              key={i}
              className={`rounded px-3 py-1 text-xs font-medium ${
                a.primary
                  ? "bg-blue-600 text-white hover:bg-blue-700"
                  : "bg-white text-gray-700 hover:bg-gray-50 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
              }`}
              onClick={() => console.log("action:", a.action)}
            >
              {a.label}
            </button>
          ))}
        </div>
      )}
      {block.footer && (
        <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">{block.footer}</p>
      )}
    </div>
  );
}
