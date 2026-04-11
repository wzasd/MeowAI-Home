/** EvidenceCard — single evidence result card. */

import type { EvidenceResult, EvidenceConfidence, EvidenceSourceType, EvidenceStatus } from "../../hooks/useEvidence";

const SOURCE_CONFIG: Record<EvidenceSourceType, { icon: string; label: string }> = {
  decision: { icon: "📋", label: "决策" },
  phase: { icon: "📊", label: "阶段" },
  discussion: { icon: "💬", label: "讨论" },
  commit: { icon: "📝", label: "提交" },
};

const STATUS_CONFIG: Record<EvidenceStatus, { label: string; className: string }> = {
  draft: { label: "草稿", className: "border-dashed opacity-80" },
  pending: { label: "待审", className: "ring-1 ring-amber-400/30" },
  published: { label: "正式", className: "" },
  archived: { label: "归档", className: "grayscale opacity-60" },
};

const CONFIDENCE_STYLES: Record<EvidenceConfidence, { bg: string; text: string; label: string }> = {
  high: { bg: "bg-emerald-900/50", text: "text-emerald-300", label: "高置信度" },
  mid: { bg: "bg-amber-900/50", text: "text-amber-300", label: "中置信度" },
  low: { bg: "bg-slate-700", text: "text-slate-400", label: "低置信度" },
};

export function EvidenceCard({ result }: { result: EvidenceResult }) {
  const source = SOURCE_CONFIG[result.source_type];
  const conf = CONFIDENCE_STYLES[result.confidence];
  const status = result.status ? STATUS_CONFIG[result.status] : null;

  const snippet = result.snippet.length > 160 ? `${result.snippet.slice(0, 160)}...` : result.snippet;

  return (
    <div
      className={`flex gap-2.5 rounded-xl border border-slate-700 bg-slate-900/80 p-3 transition-all duration-200 hover:border-slate-500 hover:shadow-sm ${status?.className ?? ""}`}
    >
      {/* Source type icon */}
      <div className="mt-0.5 flex-shrink-0">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-700 text-slate-300 transition-transform group-hover:scale-110">
          <span className="text-sm">{source.icon}</span>
        </div>
      </div>

      {/* Content */}
      <div className="min-w-0 flex-1">
        <div className="flex items-start justify-between gap-2">
          <div className="flex min-w-0 flex-col gap-0.5">
            <h4
              className={`line-clamp-2 text-xs font-bold leading-snug text-slate-100 ${
                result.status === "archived" ? "line-through decoration-gray-400/50" : ""
              }`}
            >
              {result.title}
            </h4>
          </div>
          <div className="flex flex-shrink-0 flex-col items-end gap-1">
            <span
              className={`rounded-full px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${conf.bg} ${conf.text}`}
            >
              {conf.label}
            </span>
            {status && status.label !== "正式" && (
              <span className="rounded border border-amber-200 bg-amber-100 px-1 py-0.25 text-[8px] font-black text-amber-700">
                {status.label}
              </span>
            )}
          </div>
        </div>

        <p className="mt-1.5 line-clamp-2 text-[11px] leading-relaxed text-slate-400">{snippet}</p>

        <div className="mt-2 flex items-center gap-2 border-t border-slate-700 pt-2">
          <span className="text-[10px] font-bold text-slate-400">{source.label}</span>
          <span className="text-[10px] text-slate-500">·</span>
          <span className="truncate font-mono text-[10px] italic text-slate-500 opacity-70">
            {result.anchor}
          </span>
        </div>
      </div>
    </div>
  );
}
