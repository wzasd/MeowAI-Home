import { useState, useEffect } from "react";
import { ArrowDown } from "lucide-react";

interface ScrollToBottomProps {
  containerRef: React.RefObject<HTMLDivElement | null>;
}

export function ScrollToBottomButton({ containerRef }: ScrollToBottomProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const onScroll = () => {
      const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100;
      setVisible(!atBottom);
    };

    el.addEventListener("scroll", onScroll);
    return () => el.removeEventListener("scroll", onScroll);
  }, [containerRef]);

  if (!visible) return null;

  return (
    <button
      onClick={() => containerRef.current?.scrollTo({ top: containerRef.current.scrollHeight, behavior: "smooth" })}
      className="absolute bottom-20 left-1/2 z-10 -translate-x-1/2 rounded-full border border-gray-200 bg-white p-2 shadow-lg transition-all hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:hover:bg-gray-700"
    >
      <ArrowDown size={16} className="text-gray-600 dark:text-gray-400" />
    </button>
  );
}
