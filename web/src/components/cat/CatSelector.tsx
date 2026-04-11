import { useState, useEffect, useRef } from "react";
import { ChevronDown, Check, Circle } from "lucide-react";
import { useCatStore } from "../../stores/catStore";

interface CatSelectorProps {
  currentCatId: string;
  onCatChange: (catId: string) => void;
}

const CAT_EMOJIS: Record<string, string> = {
  orange: "🐱",
  inky: "🐾",
  patch: "🌸",
};

export function CatSelector({ currentCatId, onCatChange }: CatSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const cats = useCatStore((s) => s.cats);
  const fetchCats = useCatStore((s) => s.fetchCats);

  useEffect(() => {
    fetchCats();
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const currentCat = cats.find((c) => c.id === currentCatId);
  const availableCats = cats.filter((c) => c.isAvailable);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-sm hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:hover:bg-gray-600"
      >
        <span className="text-lg">{CAT_EMOJIS[currentCatId] || "🐱"}</span>
        <span className="hidden max-w-[80px] truncate sm:inline dark:text-gray-200">
          {currentCat?.displayName || currentCat?.name || "选择猫"}
        </span>
        <ChevronDown size={14} className="text-gray-400" />
      </button>

      {isOpen && (
        <div className="absolute left-0 top-full z-50 mt-1 w-56 rounded-lg border border-gray-200 bg-white py-1 shadow-lg dark:border-gray-600 dark:bg-gray-800">
          <div className="px-3 py-2 text-xs text-gray-500 dark:text-gray-400">
            选择助手
          </div>

          {availableCats.map((cat) => (
            <button
              key={cat.id}
              onClick={() => {
                onCatChange(cat.id);
                setIsOpen(false);
              }}
              className="flex w-full items-center gap-3 px-3 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              <span className="text-xl">{cat.avatar || CAT_EMOJIS[cat.id] || "🐱"}</span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="truncate text-sm font-medium dark:text-gray-200">
                    {cat.displayName || cat.name}
                  </span>
                  {cat.id === currentCatId && (
                    <Check size={14} className="text-green-500" />
                  )}
                </div>
                {cat.roles && cat.roles.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-0.5">
                    {cat.roles.slice(0, 2).map((role) => (
                      <span
                        key={role}
                        className="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"
                      >
                        {role}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              {!cat.isAvailable && (
                <Circle size={8} className="fill-red-500 text-red-500" />
              )}
            </button>
          ))}

          {availableCats.length === 0 && (
            <div className="px-3 py-4 text-center text-sm text-gray-500 dark:text-gray-400">
              暂无可用猫咪
            </div>
          )}

          <div className="mt-1 border-t border-gray-100 px-3 py-2 dark:border-gray-700">
            <button
              onClick={() => {
                setIsOpen(false);
                window.location.href = "/settings/cats";
              }}
              className="text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400"
            >
              管理猫咪 →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
