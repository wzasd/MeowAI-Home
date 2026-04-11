import { useState, useRef, useEffect } from "react";
import { Search, Clock, MessageSquare, ArrowRight, Loader2 } from "lucide-react";

interface SearchModalProps {
  isOpen: boolean;
  onClose: () => void;
}

interface SearchResult {
  id: string;
  threadName: string;
  content: string;
  role: "user" | "assistant";
  timestamp: string;
  catId?: string;
}

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function HistorySearchModal({ isOpen, onClose }: SearchModalProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      return;
    }

    const search = async () => {
      setLoading(true);
      try {
        const res = await fetch(
          `${API_BASE}/api/messages/search?q=${encodeURIComponent(query)}&limit=20`
        );
        if (res.ok) {
          const data = await res.json();
          setResults(
            (data.results ?? []).map((r: any) => ({
              id: r.messageId || r.id,
              threadName: r.threadId?.slice(0, 8) || "未知线程",
              content: r.content,
              role: "assistant" as const,
              timestamp: r.timestamp || "",
              catId: r.catId,
            }))
          );
        }
      } finally {
        setLoading(false);
      }
    };

    const timeout = setTimeout(search, 300);
    return () => clearTimeout(timeout);
  }, [query]);

  if (!isOpen) return null;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/50 pt-20" onClick={onClose}>
      <div
        className="w-full max-w-xl rounded-xl border border-gray-200 bg-white shadow-2xl dark:border-gray-700 dark:bg-gray-800"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 border-b border-gray-200 px-4 py-3 dark:border-gray-700">
          {loading ? (
            <Loader2 size={18} className="animate-spin text-gray-400" />
          ) : (
            <Search size={18} className="text-gray-400" />
          )}
          <input
            ref={inputRef}
            className="flex-1 bg-transparent text-sm text-gray-800 outline-none placeholder:text-gray-400 dark:text-gray-200"
            placeholder="搜索对话历史..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <kbd className="rounded border border-gray-200 px-1.5 py-0.5 text-[10px] text-gray-400 dark:border-gray-600">
            ESC
          </kbd>
        </div>

        <div className="max-h-80 overflow-y-auto">
          {query ? (
            results.length > 0 ? (
              results.map((result) => (
                <button
                  key={result.id}
                  className="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700/50"
                  onClick={onClose}
                >
                  <div className="mt-0.5 shrink-0">
                    {result.role === "user" ? (
                      <MessageSquare size={14} className="text-blue-500" />
                    ) : (
                      <MessageSquare size={14} className="text-green-500" />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-gray-800 dark:text-gray-200">
                        {result.threadName}
                      </span>
                      {result.catId && (
                        <span className="rounded bg-purple-50 px-1 py-0.5 text-[10px] text-purple-600 dark:bg-purple-900/30 dark:text-purple-400">
                          @{result.catId}
                        </span>
                      )}
                    </div>
                    <p className="mt-0.5 line-clamp-2 text-xs text-gray-600 dark:text-gray-400">
                      {result.content}
                    </p>
                    {result.timestamp && (
                      <span className="mt-0.5 flex items-center gap-1 text-[10px] text-gray-400">
                        <Clock size={10} /> {result.timestamp}
                      </span>
                    )}
                  </div>
                  <ArrowRight size={14} className="shrink-0 text-gray-300" />
                </button>
              ))
            ) : (
              <div className="px-4 py-8 text-center text-sm text-gray-400">
                {loading ? "搜索中..." : "无结果"}
              </div>
            )
          ) : (
            <div className="px-4 py-8 text-center text-sm text-gray-400">
              输入关键词搜索对话历史
            </div>
          )}
        </div>

        <div className="border-t border-gray-200 px-4 py-2 text-[10px] text-gray-400 dark:border-gray-700">
          <kbd className="rounded border border-gray-200 px-1 dark:border-gray-600">Ctrl+K</kbd> 快速搜索
        </div>
      </div>
    </div>
  );
}
