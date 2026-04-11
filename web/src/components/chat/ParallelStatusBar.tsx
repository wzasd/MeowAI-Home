import { RefreshCw, Check, AlertTriangle, Clock } from "lucide-react";
import { CAT_INFO } from "../../types";

interface CatStatus {
  catId: string;
  status: "streaming" | "done" | "error" | "queued";
  progress?: number;
}

interface ParallelStatusBarProps {
  cats: CatStatus[];
}

export function ParallelStatusBar({ cats }: ParallelStatusBarProps) {
  if (cats.length === 0) return null;

  const activeCount = cats.filter((c) => c.status === "streaming").length;
  const doneCount = cats.filter((c) => c.status === "done").length;

  return (
    <div className="border-b border-gray-200 bg-gray-50 px-4 py-2 dark:border-gray-700 dark:bg-gray-800">
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {activeCount > 0 ? `${activeCount} 只猫思考中` : `${doneCount}/${cats.length} 完成`}
        </span>
        <div className="flex flex-1 items-center gap-2">
          {cats.map((cat) => {
            const info = CAT_INFO[cat.catId];
            return (
              <div key={cat.catId} className="flex items-center gap-1">
                <span className="text-sm">{info?.emoji || "🐱"}</span>
                {cat.status === "streaming" && <RefreshCw size={10} className="animate-spin text-blue-500" />}
                {cat.status === "done" && <Check size={10} className="text-green-500" />}
                {cat.status === "error" && <AlertTriangle size={10} className="text-red-500" />}
                {cat.status === "queued" && <Clock size={10} className="text-gray-400" />}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
