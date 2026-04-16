/** Workspace Terminal Panel — command execution with history. */

import { useState, useRef, useEffect, useCallback } from "react";
import { Play, Trash2, Loader2 } from "lucide-react";
import type { TerminalResult } from "../../hooks/useWorkspace";

interface TerminalPanelProps {
  runCommand: (command: string) => Promise<TerminalResult>;
}

export function TerminalPanel({ runCommand }: TerminalPanelProps) {
  const [history, setHistory] = useState<Array<{ command: string } & TerminalResult>>([]);
  const [input, setInput] = useState("");
  const [running, setRunning] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const execute = useCallback(async () => {
    const cmd = input.trim();
    if (!cmd || running) return;
    setRunning(true);
    const result = await runCommand(cmd);
    setHistory((prev) => [...prev, { command: cmd, ...result }]);
    setInput("");
    setRunning(false);
  }, [input, running, runCommand]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history, running]);

  const clearHistory = () => setHistory([]);

  return (
    <div className="flex h-full flex-col bg-gray-900 text-xs text-gray-300">
      {/* Output area */}
      <div className="flex-1 overflow-auto p-2 font-mono">
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
            </div>
            {entry.stdout && (
              <pre className="mt-1 whitespace-pre-wrap text-gray-300">{entry.stdout}</pre>
            )}
            {entry.stderr && (
              <pre className="mt-1 whitespace-pre-wrap text-red-400">{entry.stderr}</pre>
            )}
            {entry.returncode !== 0 && (
              <div className="mt-1 text-[10px] text-red-500">
                [exit code: {entry.returncode}]
              </div>
            )}
          </div>
        ))}
        {running && (
          <div className="flex items-center gap-1 text-gray-400">
            <Loader2 size={12} className="animate-spin" />
            <span>执行中...</span>
          </div>
        )}
        <div ref={bottomRef} />
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
          disabled={running}
          placeholder="输入命令..."
          className="flex-1 bg-transparent text-gray-200 outline-none placeholder:text-gray-500 disabled:opacity-50"
        />
        <button
          onClick={execute}
          disabled={running || !input.trim()}
          className="rounded p-1 text-green-400 hover:bg-gray-700 disabled:opacity-50"
        >
          {running ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
        </button>
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
