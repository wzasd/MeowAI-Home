import { useChatStore, type QueueEntryResponse } from "../../stores/chatStore";

const CAT_DISPLAY: Record<string, string> = {
  orange: "阿橘",
  inky: "墨点",
  patch: "花花",
};

function catLabel(id: string) {
  return CAT_DISPLAY[id] ?? id;
}

export function InlineQueuePanel() {
  const queueEntries = useChatStore((s) => s.queueEntries);
  const queued = queueEntries.filter((e) => e.status === "queued");

  if (queued.length === 0) return null;

  return (
    <div className="mx-4 mb-2 rounded-lg border border-amber-300/40 bg-amber-50/80 dark:bg-amber-900/20 dark:border-amber-600/30">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-amber-200/50 dark:border-amber-700/30">
        <span className="text-amber-600 dark:text-amber-400 text-sm font-medium">
          排队中
        </span>
        <span className="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded-full bg-amber-500 text-white text-xs font-bold">
          {queued.length}
        </span>
      </div>

      {/* Entries */}
      <ul className="divide-y divide-amber-200/40 dark:divide-amber-700/20">
        {queued.map((entry) => (
          <QueueEntryRow key={entry.id} entry={entry} />
        ))}
      </ul>
    </div>
  );
}

function QueueEntryRow({ entry }: { entry: QueueEntryResponse }) {
  const cancelEntry = (id: string) => {
    window.dispatchEvent(
      new CustomEvent("meowai:cancel_queue_entry", { detail: { entryId: id } })
    );
  };

  const preview =
    entry.content.length > 60
      ? entry.content.slice(0, 60) + "..."
      : entry.content;

  return (
    <li className="flex items-center gap-2 px-3 py-2 group">
      {/* Target cats */}
      <div className="flex gap-1 shrink-0">
        {entry.target_cats.map((catId) => (
          <span
            key={catId}
            className="inline-block px-1.5 py-0.5 rounded text-xs font-medium bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300"
          >
            @{catLabel(catId)}
          </span>
        ))}
      </div>

      {/* Content preview */}
      <span className="flex-1 text-sm text-gray-700 dark:text-gray-300 truncate">
        {preview}
      </span>

      {/* Remove button */}
      <button
        onClick={() => cancelEntry(entry.id)}
        className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-red-500 dark:text-gray-500 dark:hover:text-red-400"
        title="移除"
      >
        <svg
          className="w-4 h-4"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M6 18L18 6M6 6l12 12"
          />
        </svg>
      </button>
    </li>
  );
}
