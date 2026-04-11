import type { MediaBlock } from "../../types/rich";
import { Image as ImageIcon } from "lucide-react";

export function MediaBlockView({ block }: { block: MediaBlock }) {
  if (block.items.length === 0) return null;

  return (
    <div
      className={`grid gap-2 ${
        block.items.length === 1
          ? "grid-cols-1"
          : block.items.length <= 4
            ? "grid-cols-2"
            : "grid-cols-3"
      }`}
    >
      {block.items.map((item, i) => (
        <div
          key={i}
          className="group relative overflow-hidden rounded-lg border border-gray-200 bg-gray-100 dark:border-gray-700 dark:bg-gray-800"
        >
          {item.url ? (
            <img
              src={item.url}
              alt={item.alt || `Media ${i + 1}`}
              className="h-auto w-full object-cover"
              loading="lazy"
            />
          ) : (
            <div className="flex h-32 items-center justify-center">
              <ImageIcon size={24} className="text-gray-400" />
            </div>
          )}
          {item.alt && (
            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent px-2 py-1">
              <span className="text-xs text-white">{item.alt}</span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
