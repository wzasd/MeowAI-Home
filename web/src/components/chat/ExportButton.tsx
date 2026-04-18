/** Export conversation button with dropdown */

import { useState, useRef, useEffect } from "react";
import { Download, Copy, Check, FileText } from "lucide-react";
import { useThreadStore } from "../../stores/threadStore";
import { useChatStore } from "../../stores/chatStore";
import { exportToMarkdown, downloadMarkdown, copyToClipboard } from "../../utils/export";

export function ExportButton() {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const currentThread = useThreadStore((s) => s.currentThread);
  const messages = useChatStore((s) => s.messages);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  if (!currentThread) return null;

  const handleDownload = () => {
    const markdown = exportToMarkdown({ thread: currentThread, messages });
    const filename = `${currentThread.name.replace(/\s+/g, "_")}_${new Date().toISOString().slice(0, 10)}`;
    downloadMarkdown(filename, markdown);
    setIsOpen(false);
  };

  const handleCopy = async () => {
    const markdown = exportToMarkdown({ thread: currentThread, messages });
    const success = await copyToClipboard(markdown);
    if (success) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
    setIsOpen(false);
  };

  return (
    <div className="relative" ref={menuRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex h-8 items-center gap-1.5 rounded-lg bg-gray-100 px-2.5 text-xs font-medium text-gray-600 transition-colors hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
        title="导出猫窝"
      >
        <FileText size={14} />
        <span className="hidden sm:inline">导出</span>
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full z-20 mt-1 w-40 overflow-hidden rounded-lg border border-gray-200 bg-white shadow-lg dark:border-gray-600 dark:bg-gray-800">
          <button
            onClick={handleDownload}
            className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-gray-700 transition-colors hover:bg-gray-50 dark:text-gray-200 dark:hover:bg-gray-700"
          >
            <Download size={14} />
            下载 Markdown
          </button>
          <button
            onClick={handleCopy}
            className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-gray-700 transition-colors hover:bg-gray-50 dark:text-gray-200 dark:hover:bg-gray-700"
          >
            {copied ? <Check size={14} className="text-green-500" /> : <Copy size={14} />}
            {copied ? "已复制" : "复制到剪贴板"}
          </button>
        </div>
      )}
    </div>
  );
}
