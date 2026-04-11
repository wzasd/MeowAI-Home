/** EvidencePanel — Hindsight evidence search results panel. */

import { EvidenceCard } from "./EvidenceCard";
import type { EvidenceResult } from "../../hooks/useEvidence";

export interface EvidenceData {
  results: EvidenceResult[];
  degraded: boolean;
  degradeReason?: string;
}

export function EvidencePanel({ data }: { data: EvidenceData }) {
  return (
    <div className="mb-6 flex justify-center">
      <div className="w-full max-w-lg rounded-2xl border border-slate-600 bg-slate-800/90 px-5 pb-4 pt-4 shadow-sm shadow-slate-900/30 backdrop-blur-sm">
        {/* Header */}
        <div className="mb-3 flex items-center justify-between px-0.5">
          <div className="flex items-center gap-2">
            <span className="text-xs font-black uppercase tracking-wide text-slate-200">
              Hindsight 检索结果
            </span>
            <span className="rounded-full bg-slate-600 px-1.5 py-0.5 text-[10px] font-bold text-slate-300">
              {data.results.length}
            </span>
          </div>
          {data.degraded && (
            <div className="flex animate-pulse items-center gap-1 text-[10px] font-bold text-amber-400">
              <span>⚠️</span>
              <span>局部模式</span>
            </div>
          )}
        </div>

        {/* Degraded info */}
        {data.degraded && (
          <div className="mb-3 rounded-lg border border-amber-800/40 bg-amber-950/30 px-3 py-2 text-[10px] italic leading-relaxed text-amber-300">
            {"\u201c"}有些记忆暂时找不到了，正在为您从本地文档中努力搜寻...{"\u201d"}
          </div>
        )}

        {/* Results */}
        {data.results.length === 0 ? (
          <div className="py-6 text-center text-xs font-medium italic text-slate-400">
            喵... 翻遍了猫砂盆也没找到相关证据
          </div>
        ) : (
          <div className="space-y-2">
            {data.results.map((result, i) => (
              <EvidenceCard key={`${result.anchor}-${i}`} result={result} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
