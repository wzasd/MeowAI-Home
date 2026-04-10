/** A2A collaboration chain - visualizes multi-cat conversation flow */

import { useState } from "react";
import { MessageCircle, ChevronDown } from "lucide-react";

interface A2ANode {
  catId: string;
  catName: string;
  content: string;
  targetCats?: string[];
}

interface A2AChainProps {
  nodes: A2ANode[];
  primaryCatId: string;
}

const CAT_COLORS: Record<string, { border: string; bg: string }> = {
  orange: { border: "border-orange-300", bg: "bg-orange-50" },
  inky: { border: "border-purple-300", bg: "bg-purple-50" },
  patch: { border: "border-pink-300", bg: "bg-pink-50" },
};

export function A2AChain({ nodes, primaryCatId }: A2AChainProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (nodes.length === 0) return null;

  const primaryColor = CAT_COLORS[primaryCatId] || {
    border: "border-gray-300",
    bg: "bg-gray-50",
  };

  // Build collaboration summary
  const catPairs: string[] = [];
  for (let i = 0; i < nodes.length - 1; i++) {
    const currentNode = nodes[i];
    const nextNode = nodes[i + 1];
    if (!currentNode || !nextNode) continue;
    if (currentNode.targetCats?.includes(nextNode.catId)) {
      catPairs.push(`${currentNode.catName} → ${nextNode.catName}`);
    }
  }

  const firstNode = nodes[0];
  const lastNode = nodes[nodes.length - 1];
  const summary =
    catPairs.length > 0 && firstNode && lastNode
      ? `${firstNode.catName} ↔ ${lastNode.catName}, ${nodes.length} 条`
      : `${nodes.length} 只猫咪参与讨论`;

  return (
    <div
      className={`my-2 overflow-hidden rounded-lg border-l-4 ${primaryColor.border} ${primaryColor.bg}`}
    >
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left transition-opacity hover:opacity-80"
      >
        <MessageCircle size={14} className="text-gray-500" />
        <span className="text-xs font-medium text-gray-600">A2A 内部讨论</span>
        <span className="text-xs text-gray-400">({summary})</span>
        <ChevronDown
          size={14}
          className={`ml-auto text-gray-400 transition-transform ${isExpanded ? "rotate-180" : ""}`}
        />
      </button>

      {isExpanded && (
        <div className="space-y-2 px-3 pb-3">
          {nodes.map((node, index) => (
            <div key={index} className="text-xs">
              <div className="flex items-center gap-2">
                <span className="font-medium text-gray-700">{node.catName}</span>
                {node.targetCats && node.targetCats.length > 0 && (
                  <span className="text-gray-400">→ {node.targetCats.join(", ")}</span>
                )}
              </div>
              <p className="mt-0.5 line-clamp-2 text-gray-600">{node.content.slice(0, 100)}...</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
