import { useChatStore, type QueueEntryResponse } from "../../stores/chatStore";

const CAT_DISPLAY: Record<string, string> = {
  orange: "阿橘",
  inky: "墨点",
  patch: "花花",
};

function catLabel(id: string) {
  return CAT_DISPLAY[id] ?? id;
}

function catPillClass(id: string) {
  if (id === "orange") return "bg-[#bd7332]/10 text-[#8e4d1f]";
  if (id === "inky") return "bg-[#8d7aa6]/12 text-[#6f5f84]";
  if (id === "patch") return "bg-[#2f7467]/10 text-[#2f7467]";
  return "bg-[#8d7aa6]/12 text-[#6f5f84]";
}

export function InlineQueuePanel() {
  const queueEntries = useChatStore((s) => s.queueEntries);
  const queued = queueEntries.filter((e) => e.status === "queued");

  if (queued.length === 0) return null;

  const hero = queued[0];
  const rest = queued.slice(1);

  return (
    <div className="mx-4 mb-2 lg:mx-6">
      {/* Queue shell */}
      <div className="overflow-hidden rounded-[22px] border border-[#8d7aa6]/28 bg-gradient-to-b from-white/52 to-white/22 shadow-[0_16px_34px_rgba(98,74,121,0.08)]">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#8d7aa6]/14">
          <div className="flex items-center gap-2.5">
            {/* Stamp icon */}
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-[#8d7aa6]/16 text-[#8d7aa6] text-sm">
              ✦
            </div>
            <div>
              <span className="text-sm font-semibold text-[var(--text-strong)]">
                待送 {queued.length} 封
              </span>
              <span className="ml-2 text-xs text-[var(--text-faint)]">
                下一条会在当前回复结束后自动送达
              </span>
            </div>
          </div>
          <button
            onClick={() => {
              queued.forEach((e) =>
                window.dispatchEvent(
                  new CustomEvent("meowai:cancel_queue_entry", { detail: { entryId: e.id } })
                )
              );
            }}
            className="text-xs text-[var(--text-faint)] hover:text-[var(--danger)]"
          >
            清空
          </button>
        </div>

        {/* Hero card — first entry */}
        <div className="m-3.5 rounded-[20px] border border-[#8d7aa6]/18 bg-gradient-to-br from-white/60 to-[#fffcf9]/96 p-4 shadow-[0_14px_28px_rgba(73,46,22,0.08)]">
          <div className="flex items-start justify-between gap-4">
            <div>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-[#8d7aa6]/12 px-2.5 py-1 text-[11px] font-bold tracking-wide text-[#8d7aa6]">
                下一条
              </span>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {hero.target_cats.map((catId) => (
                  <span
                    key={catId}
                    className={`inline-flex items-center gap-1.5 rounded-full border border-[#8d7aa6]/18 px-2.5 py-1 text-[11px] ${catPillClass(catId)}`}
                  >
                    @{catLabel(catId)}
                  </span>
                ))}
              </div>
            </div>
            <button
              onClick={() =>
                window.dispatchEvent(
                  new CustomEvent("meowai:cancel_queue_entry", { detail: { entryId: hero.id } })
                )
              }
              className="shrink-0 rounded-full border border-[#a4462a]/16 bg-white/70 px-3 py-1.5 text-xs text-[#a4462a] hover:bg-[#a4462a]/8"
            >
              撤回
            </button>
          </div>

          {/* Content — two lines max */}
          <p className="mt-3 line-clamp-2 text-sm leading-7 text-[var(--text-strong)]">
            {hero.content}
          </p>

          {/* Footnote */}
          <div className="mt-3 flex items-center justify-between text-xs text-[var(--text-faint)]">
            <span>等 {catLabel(hero.target_cats[0] ?? "")} 回复后自动送达</span>
            <span>刚刚放入发件夹</span>
          </div>
        </div>

        {/* Compact rows — subsequent entries */}
        {rest.length > 0 && (
          <div className="flex flex-col gap-2 px-3.5 pb-3.5">
            {rest.map((entry, idx) => (
              <div
                key={entry.id}
                className="grid grid-cols-[26px_1fr_auto] items-center gap-3 rounded-[16px] border border-[#8d7aa6]/12 bg-[#fffcf9]/72 px-3 py-2.5"
              >
                <div className="flex h-[26px] w-[26px] items-center justify-center rounded-full bg-[#8d7aa6]/12 text-[11px] font-bold text-[#8d7aa6]">
                  {String(idx + 2).padStart(2, "0")}
                </div>
                <div className="min-w-0">
                  <p className="truncate text-[13px] text-[var(--text-strong)]">
                    {entry.content}
                  </p>
                  <div className="mt-1 flex gap-1.5">
                    {entry.target_cats.map((catId) => (
                      <span
                        key={catId}
                        className={`rounded-full px-2 py-0.5 text-[10px] ${catPillClass(catId)}`}
                      >
                        @{catLabel(catId)}
                      </span>
                    ))}
                  </div>
                </div>
                <button
                  onClick={() =>
                    window.dispatchEvent(
                      new CustomEvent("meowai:cancel_queue_entry", { detail: { entryId: entry.id } })
                    )
                  }
                  className="text-base leading-none text-[var(--text-faint)] hover:text-[#a4462a]"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}