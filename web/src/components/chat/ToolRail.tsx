/** Tool Visibility Rail — Clowder-style CLI Output Block
 *  Live tool call display during streaming.
 *  Matches clowder's CliOutputBlock design patterns.
 */

import { useState, useEffect, useRef } from "react";
import type { ToolCallState } from "../../stores/chatStore";

interface ToolRailProps {
  tools: ToolCallState[];
  breedColor?: string;
}

/* ── Color helpers (clowder patterns) ── */

function hexToRgba(hex: string, opacity: number): string {
  const r = Number.parseInt(hex.slice(1, 3), 16);
  const g = Number.parseInt(hex.slice(3, 5), 16);
  const b = Number.parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${opacity})`;
}

function tintedDark(hex: string, ratio = 0.25, base = "#1A1625"): string {
  const parse = (h: string): [number, number, number] => {
    const r = Number.parseInt(h.slice(1, 3), 16);
    const g = Number.parseInt(h.slice(3, 5), 16);
    const b = Number.parseInt(h.slice(5, 7), 16);
    return [r, g, b];
  };
  const [r1, g1, b1] = parse(hex);
  const [r2, g2, b2] = parse(base);
  return `rgb(${Math.round(r2 + (r1 - r2) * ratio)}, ${Math.round(g2 + (g1 - g2) * ratio)}, ${Math.round(b2 + (b1 - b2) * ratio)})`;
}

function lighten(hex: string, ratio: number): string {
  const r = Number.parseInt(hex.slice(1, 3), 16);
  const g = Number.parseInt(hex.slice(3, 5), 16);
  const b = Number.parseInt(hex.slice(5, 7), 16);
  const lr = Math.round(r + (255 - r) * ratio);
  const lg = Math.round(g + (255 - g) * ratio);
  const lb = Math.round(b + (255 - b) * ratio);
  return `rgb(${lr}, ${lg}, ${lb})`;
}

const DIVIDER = "#334155";

/* ── Inline SVG icons (Lucide-style, from clowder) ── */

function ChevronIcon({ expanded }: { expanded: boolean }) {
  return (
    <svg
      aria-hidden="true"
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="transition-transform duration-150 flex-shrink-0"
      style={{ transform: expanded ? "rotate(90deg)" : "rotate(0deg)" }}
    >
      <polyline points="9 18 15 12 9 6" />
    </svg>
  );
}

function WrenchIcon({ color }: { color?: string }) {
  return (
    <svg
      aria-hidden="true"
      width="11"
      height="11"
      viewBox="0 0 24 24"
      fill="none"
      stroke={color || "#E2E8F0"}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="flex-shrink-0"
    >
      <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg
      aria-hidden="true"
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="#22D3EE"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="flex-shrink-0"
    >
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function LoaderIcon({ color }: { color?: string }) {
  return (
    <svg
      aria-hidden="true"
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke={color || "currentColor"}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className="flex-shrink-0 animate-spin"
    >
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  );
}

/* ── Tool name → human label mapping ── */

const TOOL_LABELS: Record<string, string> = {
  read_file: "Read",
  read: "Read",
  write_file: "Write",
  edit: "Write",
  execute_command: "Bash",
  bash: "Bash",
  search_files: "Grep",
  grep: "Grep",
  list_files: "Glob",
  glob: "Glob",
  post_message: "Post",
  read_session_events: "ReadSession",
  read_session_digest: "ReadDigest",
};

/* ── Primary argument extraction (clowder pattern) ── */

const ARG_KEYS = ["file_path", "command", "pattern", "url", "query", "prompt", "path"] as const;

function extractPrimaryArg(detail?: string): string | undefined {
  if (!detail) return undefined;
  try {
    const obj = JSON.parse(detail) as Record<string, unknown>;
    for (const key of ARG_KEYS) {
      const val = obj[key];
      if (typeof val === "string" && val.length > 0) {
        return truncateArg(val);
      }
    }
    for (const val of Object.values(obj)) {
      if (typeof val === "string" && val.length > 0 && val.length <= 80) {
        return truncateArg(val);
      }
    }
  } catch {
    for (const key of ARG_KEYS) {
      const re = new RegExp(`"${key}"\\s*:\\s*"([^"]+)"`);
      const m = detail.match(re);
      if (m?.[1]) return truncateArg(m[1]);
    }
  }
  return undefined;
}

function truncateArg(val: string, max = 60): string {
  return val.length > max ? `${val.slice(0, max - 3)}...` : val;
}

function cleanToolName(name: string): string {
  const arrowIdx = name.indexOf(" → ");
  return arrowIdx >= 0 ? name.slice(arrowIdx + 3) : name;
}

function buildToolLabel(toolName: string, summary: string, detail?: string): string {
  const cleaned = cleanToolName(toolName);
  const key = cleaned.toLowerCase().replace(/\(.*\)/g, "").trim();
  const label = TOOL_LABELS[key] || cleaned;
  const primaryArg = extractPrimaryArg(detail) || truncateArg(summary);
  return primaryArg ? `${label} ${primaryArg}` : label;
}

function formatDuration(ms: number): string {
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return rem > 0 ? `${m}m${rem}s` : `${m}m`;
}

/* ── Tool Row (clowder style) ── */

function ToolRow({
  tool,
  isActive,
  accent,
}: {
  tool: ToolCallState;
  isActive: boolean;
  accent: string;
}) {
  const [rowExpanded, setRowExpanded] = useState(false);
  const hasDetail = tool.detail && tool.detail !== tool.summary;
  const accentLight = lighten(accent, 0.6);
  const accentVeryLight = lighten(accent, 0.9);
  const label = buildToolLabel(tool.toolName, tool.summary, tool.detail);

  return (
    <div className="w-full">
      <button
        type="button"
        className="w-full text-left cursor-pointer rounded font-mono text-[11px] flex items-center gap-2"
        style={{
          padding: "5px 8px",
          borderRadius: 4,
          backgroundColor: isActive ? hexToRgba(accent, 0.2) : undefined,
          borderLeft: isActive ? `2px solid ${accent}` : undefined,
        }}
        onClick={() => setRowExpanded((v) => !v)}
      >
        <div className="flex items-center gap-2 min-w-0 flex-1">
          {/* Status icon */}
          {isActive ? (
            <LoaderIcon color={accentLight} />
          ) : tool.status === "completed" ? (
            <CheckIcon />
          ) : tool.status === "failed" ? (
            <span className="text-red-400 text-[10px]">✗</span>
          ) : null}
          {/* Wrench icon */}
          <WrenchIcon color={isActive ? accentVeryLight : "#E2E8F0"} />
          {/* Tool label */}
          <span className="truncate" style={{ color: isActive ? accentVeryLight : "#E2E8F0" }}>
            <span className="font-medium">{label.split(" ")[0]}</span>
            {label.includes(" ") && (
              <span style={{ color: isActive ? accentLight : "#64748B" }}>
                {` ${label.split(" ").slice(1).join(" ")}`}
              </span>
            )}
          </span>
        </div>
        {/* Duration */}
        {tool.durationMs != null && !isActive && (
          <span className="text-[10px] text-[#64748B]">{formatDuration(tool.durationMs)}</span>
        )}
        {/* Expand indicator */}
        {hasDetail && !rowExpanded && <ChevronIcon expanded={false} />}
      </button>
      {/* Detail (expandable) */}
      {rowExpanded && hasDetail && (
        <div
          className="w-full mt-1 pl-7 whitespace-pre-wrap text-[10px] break-all"
          style={{ color: "#64748B" }}
        >
          {tool.detail}
        </div>
      )}
    </div>
  );
}

/* ── Main Component ── */

export function ToolRail({ tools, breedColor }: ToolRailProps) {
  const [expanded, setExpanded] = useState(true);
  const userInteracted = useRef(false);

  if (tools.length === 0) return null;

  const accent = breedColor || "#7C3AED";
  const surface = tintedDark(accent, 0.25);
  const surfaceInner = tintedDark(accent, 0.18);

  const isStreaming = tools.some((t) => t.status === "running");
  const toolCount = tools.length;
  const completedCount = tools.filter((t) => t.status === "completed").length;
  const failedCount = tools.filter((t) => t.status === "failed").length;
  const lastRunningId = isStreaming
    ? [...tools].reverse().find((t) => t.status === "running")?.callId
    : undefined;

  // Auto-expand during streaming
  useEffect(() => {
    if (isStreaming && !expanded && !userInteracted.current) {
      setExpanded(true);
    }
  }, [isStreaming, expanded]);

  const summary = isStreaming
    ? `CLI Output · streaming · ${tools.find((t) => t.status === "running")?.toolName || ""}...`
    : `CLI Output · done · ${toolCount} tool${toolCount > 1 ? "s" : ""}`;

  return (
    <div className="mt-2 mb-1 overflow-hidden" style={{ backgroundColor: surface, borderRadius: 10 }}>
      {/* Header */}
      <button
        type="button"
        className="w-full flex items-center gap-2 text-[11px] font-mono transition-colors"
        style={{ padding: "8px 12px", color: "#94A3B8", backgroundColor: surface }}
        onClick={() => {
          userInteracted.current = true;
          setExpanded((v) => !v);
        }}
      >
        <span style={{ color: accent }}>
          <ChevronIcon expanded={expanded} />
        </span>
        <span className="font-medium">{summary}</span>
        <span className="ml-auto flex items-center gap-1" style={{ color: "#64748B", fontSize: 10 }}>
          {completedCount > 0 && <span className="text-cyan-400">{completedCount} ✓</span>}
          {failedCount > 0 && <span className="text-red-400">{failedCount} ✗</span>}
        </span>
      </button>

      {/* Expanded body */}
      {expanded && (
        <div style={{ backgroundColor: surfaceInner }}>
          <div style={{ height: 1, backgroundColor: DIVIDER }} />
          <div style={{ padding: "4px 12px" }} className="space-y-0.5">
            {tools.map((tool) => (
              <ToolRow
                key={tool.callId}
                tool={tool}
                isActive={tool.callId === lastRunningId}
                accent={accent}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
