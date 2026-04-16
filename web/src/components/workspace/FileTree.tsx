/** Workspace File Tree — recursive directory listing. */

import { useState } from "react";
import { ChevronRight, ChevronDown, Folder, FolderOpen } from "lucide-react";
import type { TreeNode } from "../../hooks/useWorkspace";

const FILE_ICONS: Record<string, string> = {
  py: "🐍",
  tsx: "⚛️",
  ts: "⚛️",
  js: "📜",
  jsx: "⚛️",
  json: "📋",
  md: "📝",
  toml: "⚙️",
  yaml: "⚙️",
  yml: "⚙️",
  css: "🎨",
  scss: "🎨",
  html: "🌐",
  rs: "🦀",
  go: "🐹",
  java: "☕",
};

interface FileTreeItemProps {
  node: TreeNode;
  depth: number;
  selectedPath: string | null;
  onSelect: (path: string) => void;
  onExpand: (path: string) => void;
}

function FileTreeItem({ node, depth, selectedPath, onSelect, onExpand }: FileTreeItemProps) {
  const [expanded, setExpanded] = useState(depth < 2);
  const isDir = node.type === "directory";
  const isSelected = selectedPath === node.path;
  const ext = node.name.split(".").pop()?.toLowerCase() || "";

  const handleClick = () => {
    if (isDir) {
      setExpanded(!expanded);
      if (!expanded && !node.children) {
        onExpand(node.path);
      }
    }
    onSelect(node.path);
  };

  return (
    <div>
      <button
        onClick={handleClick}
        className={`flex w-full items-center gap-1 rounded px-2 py-0.5 text-xs hover:bg-gray-100 dark:hover:bg-gray-700 ${
          isSelected
            ? "bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
            : "text-gray-700 dark:text-gray-300"
        }`}
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
      >
        {isDir ? (
          expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />
        ) : (
          <span className="w-3" />
        )}
        {isDir ? (
          expanded ? (
            <FolderOpen size={12} className="text-amber-500" />
          ) : (
            <Folder size={12} className="text-amber-500" />
          )
        ) : (
          <span className="text-[10px]">{FILE_ICONS[ext] || "📄"}</span>
        )}
        <span className="truncate">{node.name}</span>
      </button>
      {isDir && expanded && node.children?.map((child) => (
        <FileTreeItem
          key={child.path}
          node={child}
          depth={depth + 1}
          selectedPath={selectedPath}
          onSelect={onSelect}
          onExpand={onExpand}
        />
      ))}
    </div>
  );
}

export interface FileTreeProps {
  tree: TreeNode[];
  selectedPath: string | null;
  onSelect: (path: string) => void;
  onExpand: (path: string) => void;
}

export function FileTree({ tree, selectedPath, onSelect, onExpand }: FileTreeProps) {
  return (
    <div className="h-full overflow-y-auto">
      {tree.map((node) => (
        <FileTreeItem
          key={node.path}
          node={node}
          depth={0}
          selectedPath={selectedPath}
          onSelect={onSelect}
          onExpand={onExpand}
        />
      ))}
    </div>
  );
}
