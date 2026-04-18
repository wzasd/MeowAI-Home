/** Workspace Terminal Panel — streaming command execution with history. */

import { useState, useRef, useEffect, useCallback } from "react";
import { Play, Trash2, Loader2, Square, AlertCircle } from "lucide-react";
import { useWorkspace } from "../../hooks/useWorkspace";
import type { TerminalJobEvent } from "../../api/client";

interface OutputLine {
  type: "stdout" | "stderr" | "system";
  text: string;
}

interface JobEntry {
  command: string;
  status: string;
  lines: OutputLine[];
  returncode: number | null;
  progress?: { parser: string; stage?: string; percent?: number; detail: string };
  waitingInput?: boolean;
}

export function TerminalPanel() {
  const { createTerminalJob, cancelTerminalJob, streamTerminalJob } = useWorkspace();

  const [history, setHistory] = useState<JobEntry[]>([]);
  const [input, setInput] = useState("");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [activeStatus, setActiveStatus] = useState<string | null>(null);
  const [activeProgress, setActiveProgress] = useState<JobEntry["progress"]>(undefined);
  const [waitingInput, setWaitingInput] = useState(false);

  const outputRef = useRef<HTMLDivElement>(null);
  const outputBufferRef = useRef<{ jobIndex: number; line: OutputLine }[]>([]);
  const rafRef = useRef<number | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Scroll only inside terminal output, never the whole page.
  useEffect(() => {
    const container = outputRef.current;
    if (!container) return;
    container.scrollTo({ top: container.scrollHeight, behavior: "smooth" });
  }, [history, activeStatus, waitingInput]);

  // RAF batching: flush buffer into history state
  const flushBuffer = useCallback(() => {
    if (outputBufferRef.current.length === 0) return;
    const batch = outputBufferRef.current.splice(0);
    setHistory((prev) => {
      const next = [...prev];
      for (const { jobIndex, line } of batch) {
        if (jobIndex >= 0 && jobIndex < next.length) {
          next[jobIndex]!.lines.push(line);
        }
      }
      return next;
    });
    rafRef.current = null;
  }, []);

  const scheduleFlush = useCallback(() => {
    if (rafRef.current === null) {
      rafRef.current = requestAnimationFrame(flushBuffer);
    }
  }, [flushBuffer]);

  useEffect(() => {
    return () => {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
      }
      abortRef.current?.abort();
    };
  }, []);

  const execute = useCallback(async () => {
    const cmd = input.trim();
    if (!cmd || activeJobId) return;

    const res = await createTerminalJob(cmd);
    if (!res) {
      setHistory((prev) => [
        ...prev,
        { command: cmd, status: "failed", lines: [{ type: "stderr", text: "Failed to create job" }], returncode: -1 },
      ]);
      return;
    }

    const jobId = res.job_id;
    const jobIndex = history.length;
    setHistory((prev) => [
      ...prev,
      { command: cmd, status: "starting", lines: [], returncode: null },
    ]);
    setActiveJobId(jobId);
    setActiveStatus("starting");
    setActiveProgress(undefined);
    setWaitingInput(false);
    setInput("");

    const handleEvent = (event: TerminalJobEvent) => {
      switch (event.type) {
        case "status":
          setActiveStatus(event.status);
          break;
        case "started":
          setActiveStatus("running");
          break;
        case "stdout":
        case "stderr":
          outputBufferRef.current.push({ jobIndex, line: { type: event.type, text: event.text } });
          scheduleFlush();
          break;
        case "progress":
          setActiveProgress({
            parser: event.parser,
            stage: event.stage,
            percent: event.percent,
            detail: event.detail,
          });
          break;
        case "waiting_input":
          setWaitingInput(true);
          setActiveStatus("waiting_input");
          break;
        case "heartbeat":
          if ("state" in event && event.state !== "active") {
            setActiveStatus(event.state);
          }
          break;
        case "exited":
          setActiveStatus(event.status);
          setHistory((prev) => {
            const next = [...prev];
            if (jobIndex >= 0 && jobIndex < next.length) {
              next[jobIndex]!.status = event.status;
              next[jobIndex]!.returncode = event.returncode;
            }
            return next;
          });
          setActiveJobId(null);
          setWaitingInput(false);
          abortRef.current = null;
          break;
        case "timeout":
        case "error":
          setActiveStatus(event.type === "timeout" ? event.status : "failed");
          setHistory((prev) => {
            const next = [...prev];
            if (jobIndex >= 0 && jobIndex < next.length) {
              next[jobIndex]!.status = event.type === "timeout" ? event.status : "failed";
              next[jobIndex]!.returncode = -1;
              if (event.type === "error") {
                next[jobIndex]!.lines.push({ type: "stderr", text: event.message });
              }
            }
            return next;
          });
          setActiveJobId(null);
          setWaitingInput(false);
          abortRef.current = null;
          break;
      }
    };

    abortRef.current = streamTerminalJob(jobId, handleEvent, () => {
      setActiveJobId(null);
    });
  }, [input, activeJobId, history.length, createTerminalJob, streamTerminalJob, scheduleFlush]);

  const handleCancel = useCallback(async () => {
    if (!activeJobId) return;
    await cancelTerminalJob(activeJobId);
  }, [activeJobId, cancelTerminalJob]);

  const clearHistory = () => {
    setHistory([]);
    outputBufferRef.current = [];
  };

  const statusColor = (status: string) => {
    switch (status) {
      case "running":
        return "bg-blue-500";
      case "quiet":
        return "bg-amber-500";
      case "stalled":
        return "bg-red-500";
      case "waiting_input":
        return "bg-purple-500";
      case "done":
        return "bg-green-500";
      case "failed":
      case "timeout":
        return "bg-red-500";
      case "cancelled":
        return "bg-gray-500";
      default:
        return "bg-gray-400";
    }
  };

  return (
    <div className="flex h-full flex-col bg-gray-900 text-xs text-gray-300">
      {/* Status bar */}
      {(activeJobId || activeStatus) && (
        <div className="flex items-center gap-2 border-b border-gray-700 bg-gray-800 px-2 py-1">
          <span className={`h-2 w-2 rounded-full ${statusColor(activeStatus || "")}`} />
          <span className="text-[10px] uppercase text-gray-400">{activeStatus}</span>
          {activeProgress?.percent !== undefined && (
            <div className="ml-2 flex flex-1 items-center gap-2">
              <div className="h-1.5 flex-1 rounded bg-gray-700">
                <div
                  className="h-1.5 rounded bg-blue-500"
                  style={{ width: `${Math.min(100, activeProgress.percent)}%` }}
                />
              </div>
              <span className="text-[10px] text-gray-400">{activeProgress.percent}%</span>
            </div>
          )}
          {activeProgress && activeProgress.percent === undefined && (
            <span className="ml-2 text-[10px] text-gray-400">{activeProgress.detail}</span>
          )}
          {activeJobId && (
            <button
              onClick={handleCancel}
              className="ml-auto flex items-center gap-1 rounded bg-red-600/20 px-1.5 py-0.5 text-[10px] text-red-400 hover:bg-red-600/30"
            >
              <Square size={10} /> 中断
            </button>
          )}
        </div>
      )}

      {/* Waiting input banner */}
      {waitingInput && (
        <div className="flex items-center gap-1 bg-purple-900/20 px-2 py-1 text-[10px] text-purple-300">
          <AlertCircle size={10} />
          <span>命令正在等待输入（当前版本不支持交互式输入）</span>
        </div>
      )}

      {/* Output area */}
      <div ref={outputRef} className="flex-1 overflow-auto p-2 font-mono">
        {history.length === 0 && (
          <div className="text-gray-500">在下方输入命令并按回车执行...</div>
        )}
        {history.map((entry, idx) => (
          <div key={idx} className="mb-2">
            <div className="flex items-center gap-1 text-green-400">
              <span>meowai@home</span>
              <span className="text-gray-500">:</span>
              <span className="text-blue-400">~</span>
              <span className="text-gray-500">$</span>
              <span className="text-gray-200">{entry.command}</span>
              {entry.status && entry.status !== "running" && entry.status !== "starting" && (
                <span className={`ml-1 text-[10px] ${statusColor(entry.status).replace("bg-", "text-")}`}>
                  [{entry.status}]
                </span>
              )}
            </div>
            {entry.lines.map((line, lidx) => (
              <pre
                key={lidx}
                className={`mt-0.5 whitespace-pre-wrap ${
                  line.type === "stderr" ? "text-red-400" : "text-gray-300"
                }`}
              >
                {line.text}
              </pre>
            ))}
            {entry.returncode !== null && entry.returncode !== 0 && (
              <div className="mt-1 text-[10px] text-red-500">[exit code: {entry.returncode}]</div>
            )}
          </div>
        ))}
        {activeJobId && activeStatus && activeStatus !== "running" && activeStatus !== "starting" && (
          <div className="flex items-center gap-1 text-gray-400">
            <Loader2 size={12} className="animate-spin" />
            <span>执行中...</span>
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="flex items-center gap-2 border-t border-gray-700 bg-gray-800 px-2 py-1.5">
        <span className="shrink-0 text-green-400">$</span>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") execute();
          }}
          disabled={!!activeJobId}
          placeholder="输入命令..."
          className="flex-1 bg-transparent text-gray-200 outline-none placeholder:text-gray-500 disabled:opacity-50"
        />
        {activeJobId ? (
          <button
            onClick={handleCancel}
            className="rounded p-1 text-red-400 hover:bg-gray-700"
          >
            <Square size={14} />
          </button>
        ) : (
          <button
            onClick={execute}
            disabled={!input.trim()}
            className="rounded p-1 text-green-400 hover:bg-gray-700 disabled:opacity-50"
          >
            <Play size={14} />
          </button>
        )}
        <button
          onClick={clearHistory}
          className="rounded p-1 text-gray-400 hover:bg-gray-700 hover:text-red-400"
          title="清空历史"
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  );
}
