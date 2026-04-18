import { useState } from "react";
import { useCatStore } from "../../stores/catStore";
import { Check, Code, Search, MessageSquare, GitBranch, Shield, BarChart3 } from "lucide-react";

const CAPABILITY_GROUPS = [
  {
    name: "核心能力",
    items: [
      { id: "code_gen", label: "代码生成", icon: Code, desc: "生成高质量代码" },
      { id: "code_review", label: "代码审查", icon: Search, desc: "审查代码质量" },
      { id: "chat", label: "猫窝", icon: MessageSquare, desc: "自然语言猫窝" },
      { id: "git_ops", label: "Git 操作", icon: GitBranch, desc: "版本控制操作" },
    ],
  },
  {
    name: "安全与治理",
    items: [
      { id: "security_scan", label: "安全扫描", icon: Shield, desc: "检测安全漏洞" },
      { id: "cost_analysis", label: "成本分析", icon: BarChart3, desc: "分析 Token 使用成本" },
    ],
  },
];

export function CapabilitySettings() {
  const cats = useCatStore((s) => s.cats);
  const updateCat = useCatStore((s) => s.updateCat);
  const fetchCats = useCatStore((s) => s.fetchCats);
  const [selectedCat, setSelectedCat] = useState<string | null>(cats[0]?.id || null);
  const [toggling, setToggling] = useState<string | null>(null);

  const cat = cats.find((c) => c.id === selectedCat);

  const handleToggle = async (capId: string) => {
    if (!cat) return;
    const currentCaps = cat.capabilities || [];
    const newCaps = currentCaps.includes(capId)
      ? currentCaps.filter((c) => c !== capId)
      : [...currentCaps, capId];

    setToggling(capId);
    try {
      await updateCat(cat.id, { capabilities: newCaps });
      await fetchCats();
    } catch (err) {
      console.error("Failed to update capabilities:", err);
    } finally {
      setToggling(null);
    }
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600 dark:text-gray-400">
        配置每只猫咪的能力范围。启用/禁用特定功能以控制 Agent 行为。
      </p>

      {/* Cat selector */}
      <div className="flex flex-wrap gap-2">
        {cats.map((c) => (
          <button
            key={c.id}
            onClick={() => setSelectedCat(c.id)}
            className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm ${
              selectedCat === c.id
                ? "border-blue-300 bg-blue-50 text-blue-700 dark:border-blue-700 dark:bg-blue-900/20 dark:text-blue-400"
                : "border-gray-200 text-gray-600 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-400 dark:hover:bg-gray-700"
            }`}
          >
            {c.displayName || c.name}
            {c.isAvailable && <Check size={12} className="text-green-500" />}
          </button>
        ))}
      </div>

      {/* Capability groups */}
      {cat && (
        <div className="space-y-4">
          {CAPABILITY_GROUPS.map((group) => (
            <div key={group.name}>
              <h4 className="mb-2 text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">{group.name}</h4>
              <div className="grid gap-2 sm:grid-cols-2">
                {group.items.map((cap) => {
                  const Icon = cap.icon;
                  const enabled = cat.capabilities?.includes(cap.id) ?? false;
                  const isToggling = toggling === cap.id;
                  return (
                    <button
                      key={cap.id}
                      onClick={() => handleToggle(cap.id)}
                      disabled={isToggling}
                      className={`flex items-start gap-3 rounded-lg border p-3 text-left transition-colors ${
                        enabled
                          ? "border-green-200 bg-green-50/50 dark:border-green-800 dark:bg-green-900/10"
                          : "border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
                      } ${isToggling ? "opacity-60" : "cursor-pointer hover:shadow-sm"}`}
                    >
                      <Icon size={16} className={`mt-0.5 ${enabled ? "text-green-600" : "text-gray-400"}`} />
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-gray-800 dark:text-gray-200">{cap.label}</span>
                          {enabled ? (
                            <span className="rounded bg-green-100 px-1.5 py-0.5 text-[10px] text-green-700 dark:bg-green-900/30 dark:text-green-400">
                              已启用
                            </span>
                          ) : (
                            <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-500 dark:bg-gray-700 dark:text-gray-400">
                              已禁用
                            </span>
                          )}
                        </div>
                        <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">{cap.desc}</p>
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
