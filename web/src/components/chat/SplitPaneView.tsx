/** Split Pane 2x2 multi-thread view */

import { useState } from "react";
import { X, Plus, Grid2x2 } from "lucide-react";
import { ChatArea } from "./ChatArea";

interface Pane {
  id: string;
  threadId: string | null;
}

export function SplitPaneView() {
  const [panes, setPanes] = useState<Pane[]>([
    { id: "1", threadId: null },
    { id: "2", threadId: null },
  ]);
  const [layout, setLayout] = useState<"2x1" | "2x2">("2x1");

  const addPane = () => {
    if (panes.length >= 4) return;
    setPanes([...panes, { id: String(panes.length + 1), threadId: null }]);
    if (panes.length === 1) setLayout("2x2");
  };

  const removePane = (id: string) => {
    if (panes.length <= 1) return;
    setPanes(panes.filter((p) => p.id !== id));
    if (panes.length === 3) setLayout("2x1");
  };

  return (
    <div className="flex h-full flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-2 dark:border-gray-700 dark:bg-gray-800">
        <div className="flex items-center gap-2">
          <Grid2x2 size={16} className="text-gray-500" />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">分屏视图</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setLayout("2x1")}
            className={`rounded px-2 py-1 text-xs ${layout === "2x1" ? "bg-blue-100 text-blue-700" : "text-gray-500 hover:bg-gray-100"}`}
          >
            2列
          </button>
          <button
            onClick={() => setLayout("2x2")}
            className={`rounded px-2 py-1 text-xs ${layout === "2x2" ? "bg-blue-100 text-blue-700" : "text-gray-500 hover:bg-gray-100"}`}
          >
            2x2
          </button>
          {panes.length < 4 && (
            <button
              onClick={addPane}
              className="flex items-center gap-1 rounded bg-blue-600 px-2 py-1 text-xs text-white hover:bg-blue-700"
            >
              <Plus size={12} /> 添加
            </button>
          )}
        </div>
      </div>

      {/* Panes grid */}
      <div className={`flex-1 gap-2 p-2 ${layout === "2x2" ? "grid grid-cols-2 grid-rows-2" : "grid grid-cols-2"}`}>
        {panes.map((pane) => (
          <div key={pane.id} className="relative flex flex-col overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
            <div className="flex items-center justify-between border-b border-gray-200 bg-gray-50 px-2 py-1 dark:border-gray-700 dark:bg-gray-800">
              <span className="text-xs text-gray-500">面板 {pane.id}</span>
              {panes.length > 1 && (
                <button
                  onClick={() => removePane(pane.id)}
                  className="rounded p-0.5 text-gray-400 hover:bg-gray-200 hover:text-red-500"
                >
                  <X size={12} />
                </button>
              )}
            </div>
            <div className="flex-1 overflow-hidden">
              <ChatArea />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
