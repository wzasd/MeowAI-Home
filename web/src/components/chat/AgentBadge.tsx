import { CAT_INFO } from "../../types";

interface AgentBadgeProps {
  catId: string;
}

export function AgentBadge({ catId }: AgentBadgeProps) {
  const info = CAT_INFO[catId] || { name: catId, emoji: "🐾", color: "gray" };
  const colorClasses: Record<string, string> = {
    orange: "bg-orange-100 text-orange-700",
    purple: "bg-purple-100 text-purple-700",
    pink: "bg-pink-100 text-pink-700",
    gray: "bg-gray-100 text-gray-700",
  };

  return (
    <div className="mr-2 shrink-0 self-end">
      <div
        className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-medium ${
          colorClasses[info.color] || colorClasses.gray
        }`}
        title={info.name}
      >
        {info.emoji}
      </div>
    </div>
  );
}
