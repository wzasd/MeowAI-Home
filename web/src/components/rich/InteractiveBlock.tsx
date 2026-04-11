import { useState } from "react";
import type { InteractiveBlock } from "../../types/rich";
import { ChevronDown } from "lucide-react";

export function InteractiveBlockView({ block }: { block: InteractiveBlock }) {
  const [selected, setSelected] = useState<string[]>([]);

  if (block.style === "confirm") {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-800 dark:bg-amber-900/20">
        <p className="text-sm text-gray-800 dark:text-gray-200">{block.prompt}</p>
        <div className="mt-2 flex gap-2">
          {block.options.map((opt) => (
            <button
              key={opt.value}
              className={`rounded px-3 py-1 text-xs font-medium ${
                opt.value === "yes"
                  ? "bg-green-600 text-white hover:bg-green-700"
                  : "bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-600 dark:text-gray-300"
              }`}
              onClick={() => console.log("confirm:", opt.value)}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
    );
  }

  if (block.style === "button_group") {
    return (
      <div className="flex flex-wrap gap-2">
        {block.options.map((opt) => (
          <button
            key={opt.value}
            className={`rounded border px-3 py-1.5 text-xs font-medium transition-colors ${
              selected.includes(opt.value)
                ? "border-blue-500 bg-blue-50 text-blue-700 dark:border-blue-400 dark:bg-blue-900/30 dark:text-blue-300"
                : "border-gray-200 bg-white text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
            }`}
            onClick={() => setSelected((prev) =>
              prev.includes(opt.value) ? prev.filter((v) => v !== opt.value) : [...prev, opt.value]
            )}
          >
            {opt.label}
          </button>
        ))}
      </div>
    );
  }

  // select / multi_select
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
      <p className="mb-2 text-sm text-gray-700 dark:text-gray-300">{block.prompt}</p>
      <div className="relative">
        <select
          className="w-full appearance-none rounded border border-gray-300 bg-white px-3 py-1.5 pr-8 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
          value={selected[0] || ""}
          onChange={(e) => setSelected([e.target.value])}
        >
          <option value="" disabled>
            选择...
          </option>
          {block.options.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
        <ChevronDown size={14} className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-gray-400" />
      </div>
    </div>
  );
}
