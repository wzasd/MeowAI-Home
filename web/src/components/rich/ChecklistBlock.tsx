import { useState } from "react";
import type { ChecklistBlock } from "../../types/rich";
import { CheckSquare, Square } from "lucide-react";

export function ChecklistBlockView({ block }: { block: ChecklistBlock }) {
  const [items, setItems] = useState(block.items);
  const checked = items.filter((i) => i.checked).length;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
      {block.title && (
        <div className="mb-2 flex items-center justify-between">
          <h4 className="text-sm font-semibold text-gray-800 dark:text-gray-200">{block.title}</h4>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {checked}/{items.length}
          </span>
        </div>
      )}
      <ul className="space-y-1">
        {items.map((item) => (
          <li
            key={item.id}
            className="flex cursor-pointer items-center gap-2 rounded px-1 py-0.5 hover:bg-gray-50 dark:hover:bg-gray-700/50"
            onClick={() =>
              setItems((prev) =>
                prev.map((i) => (i.id === item.id ? { ...i, checked: !i.checked } : i))
              )
            }
          >
            {item.checked ? (
              <CheckSquare size={14} className="shrink-0 text-blue-500" />
            ) : (
              <Square size={14} className="shrink-0 text-gray-400" />
            )}
            <span
              className={`text-sm ${
                item.checked
                  ? "text-gray-400 line-through dark:text-gray-500"
                  : "text-gray-700 dark:text-gray-300"
              }`}
            >
              {item.text}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
