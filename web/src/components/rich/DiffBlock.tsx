import type { DiffBlock } from "../../types/rich";

export function DiffBlockView({ block }: { block: DiffBlock }) {
  return (
    <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
      {block.summary && (
        <div className="border-b border-gray-200 bg-gray-50 px-3 py-1.5 text-xs text-gray-600 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-400">
          {block.summary}
        </div>
      )}
      <div className="overflow-x-auto bg-gray-900 p-3 font-mono text-xs leading-relaxed">
        {block.hunks.map((hunk, hi) => (
          <div key={hi} className="mb-3 last:mb-0">
            {(hunk.oldPath || hunk.newPath) && (
              <div className="mb-1 text-gray-400">
                {hunk.newPath || hunk.oldPath}
              </div>
            )}
            <pre className="whitespace-pre">
              {hunk.content.split("\n").map((line, li) => (
                <div
                  key={li}
                  className={
                    line.startsWith("+")
                      ? "bg-green-900/30 text-green-300"
                      : line.startsWith("-")
                        ? "bg-red-900/30 text-red-300"
                        : line.startsWith("@@")
                          ? "text-blue-400"
                          : "text-gray-300"
                  }
                >
                  {line}
                </div>
              ))}
            </pre>
          </div>
        ))}
      </div>
    </div>
  );
}
