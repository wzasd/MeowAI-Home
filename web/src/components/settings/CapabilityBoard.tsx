import { useState, useEffect, useCallback } from "react";
import { useCatStore } from "../../stores/catStore";
import { useThreadStore } from "../../stores/threadStore";
import { api } from "../../api/client";
import { Loader2, ToggleLeft, ToggleRight, Server, Wrench, Activity } from "lucide-react";
import type { CapabilityBoardItem } from "../../types";

export function CapabilityBoard() {
  const cats = useCatStore((s) => s.cats);
  const currentThread = useThreadStore((s) => s.currentThread);
  const [projectPath, setProjectPath] = useState("");
  const [items, setItems] = useState<CapabilityBoardItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toggling, setToggling] = useState<string | null>(null);
  const [probing, setProbing] = useState(false);

  // Default project path from current thread
  useEffect(() => {
    if (currentThread?.project_path) {
      setProjectPath(currentThread.project_path);
    }
  }, [currentThread?.project_path]);

  const fetchBoard = useCallback(async (probe = false) => {
    if (!projectPath.trim()) {
      setItems([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await api.capabilities.get(projectPath.trim(), probe);
      setItems(data.items || []);
    } catch (e: any) {
      setError(e.message || "加载能力看板失败");
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [projectPath]);

  useEffect(() => {
    fetchBoard(false);
  }, [fetchBoard]);

  const handleToggle = async (
    item: CapabilityBoardItem,
    scope: "global" | "cat",
    enabled: boolean,
    catId?: string
  ) => {
    const key = `${item.id}:${scope}:${catId || "global"}`;
    setToggling(key);
    try {
      await api.capabilities.patch({
        capabilityId: item.id,
        capabilityType: item.type,
        scope,
        enabled,
        catId,
        projectPath: projectPath.trim(),
      });
      await fetchBoard();
    } catch (e: any) {
      setError(e.message || "更新失败");
    } finally {
      setToggling(null);
    }
  };

  const mcpItems = items.filter((i) => i.type === "mcp");
  const skillItems = items.filter((i) => i.type === "skill");

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600 dark:text-gray-400">
        管理项目级能力编排。启用/禁用 MCP 和 Skill，支持全局开关和每只猫咪的独立覆盖。
      </p>

      <div className="flex items-center gap-2">
        <input
          type="text"
          value={projectPath}
          onChange={(e) => setProjectPath(e.target.value)}
          placeholder="输入项目路径"
          className="flex-1 rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-800 dark:text-gray-200"
        />
        <button
          type="button"
          onClick={() => fetchBoard(false)}
          disabled={loading || !projectPath.trim()}
          className="rounded bg-blue-500 px-3 py-1.5 text-sm text-white hover:bg-blue-600 disabled:opacity-50"
        >
          {loading ? <Loader2 size={16} className="animate-spin" /> : "加载"}
        </button>
        <button
          type="button"
          onClick={async () => {
            setProbing(true);
            await fetchBoard(true);
            setProbing(false);
          }}
          disabled={loading || probing || !projectPath.trim()}
          className="flex items-center gap-1 rounded bg-emerald-500 px-3 py-1.5 text-sm text-white hover:bg-emerald-600 disabled:opacity-50"
        >
          {probing ? <Loader2 size={16} className="animate-spin" /> : <Activity size={16} />}
          探测
        </button>
      </div>

      {error && (
        <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-500 dark:bg-red-900/20 dark:text-red-400">
          {error}
        </div>
      )}

      {items.length === 0 && !loading && projectPath.trim() && (
        <div className="py-8 text-center text-gray-400">
          <p className="text-sm">暂无能力配置</p>
          <p className="mt-1 text-xs">该项目尚未生成 capabilities.json</p>
        </div>
      )}

      {mcpItems.length > 0 && (
        <CapabilitySection
          title="MCP 服务器"
          icon={Server}
          items={mcpItems}
          cats={cats}
          toggling={toggling}
          onToggle={handleToggle}
          showProbe
        />
      )}

      {skillItems.length > 0 && (
        <CapabilitySection
          title="Skills"
          icon={Wrench}
          items={skillItems}
          cats={cats}
          toggling={toggling}
          onToggle={handleToggle}
        />
      )}
    </div>
  );
}

interface CapabilitySectionProps {
  title: string;
  icon: React.ElementType;
  items: CapabilityBoardItem[];
  cats: { id: string; displayName?: string; name: string }[];
  toggling: string | null;
  onToggle: (item: CapabilityBoardItem, scope: "global" | "cat", enabled: boolean, catId?: string) => Promise<void>;
  showProbe?: boolean;
}

function CapabilitySection({ title, icon: Icon, items, cats, toggling, onToggle, showProbe }: CapabilitySectionProps) {
  return (
    <div>
      <h4 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">
        <Icon size={14} />
        {title}
      </h4>
      <div className="overflow-hidden rounded-lg border border-gray-200 dark:border-gray-700">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left dark:bg-gray-800">
            <tr>
              <th className="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">名称</th>
              <th className="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">来源</th>
              <th className="px-3 py-2 font-medium text-gray-500 dark:text-gray-400">全局</th>
              {cats.map((cat) => (
                <th key={cat.id} className="px-2 py-2 text-center font-medium text-gray-500 dark:text-gray-400">
                  {cat.displayName || cat.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-700">
            {items.map((item) => {
              const globalKey = `${item.id}:global:global`;
              return (
                <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                  <td className="px-3 py-2">
                    <div className="font-medium text-gray-800 dark:text-gray-200">{item.id}</div>
                    {item.description && (
                      <div className="max-w-xs truncate text-[10px] text-gray-500 dark:text-gray-400">{item.description}</div>
                    )}
                    {showProbe && item.connectionStatus && (
                      <div className="mt-1 flex items-center gap-1.5 text-[10px]">
                        <span
                          className={[
                            "inline-block h-1.5 w-1.5 rounded-full",
                            item.connectionStatus === "connected" ? "bg-green-500" : "",
                            item.connectionStatus === "timeout" ? "bg-amber-500" : "",
                            item.connectionStatus === "error" ? "bg-red-500" : "",
                            item.connectionStatus === "unsupported" ? "bg-gray-400" : "",
                          ].join(" ")}
                        />
                        <span
                          className={[
                            item.connectionStatus === "connected" ? "text-green-600 dark:text-green-400" : "",
                            item.connectionStatus === "timeout" ? "text-amber-600 dark:text-amber-400" : "",
                            item.connectionStatus === "error" ? "text-red-600 dark:text-red-400" : "",
                            item.connectionStatus === "unsupported" ? "text-gray-500 dark:text-gray-400" : "",
                          ].join(" ")}
                        >
                          {item.connectionStatus === "connected" && `已连接 · ${(item.tools || []).length} 工具`}
                          {item.connectionStatus === "timeout" && "探测超时"}
                          {item.connectionStatus === "error" && (item.probeError || "连接错误")}
                          {item.connectionStatus === "unsupported" && "不支持探测"}
                        </span>
                      </div>
                    )}
                    {item.type === "skill" && item.triggers && item.triggers.length > 0 && (
                      <div className="mt-1 flex flex-wrap gap-1">
                        {item.triggers.map((t) => (
                          <span
                            key={t}
                            className="rounded bg-amber-50 px-1.5 py-0.5 text-[10px] text-amber-600 dark:bg-amber-900/20 dark:text-amber-400"
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    )}
                  </td>
                  <td className="px-3 py-2">
                    <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                      {item.source}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <button
                      type="button"
                      onClick={() => onToggle(item, "global", !item.enabled)}
                      disabled={toggling === globalKey}
                      className="disabled:opacity-50"
                    >
                      {item.enabled ? (
                        <ToggleRight size={20} className="text-green-500" />
                      ) : (
                        <ToggleLeft size={20} className="text-gray-400" />
                      )}
                    </button>
                  </td>
                  {cats.map((cat) => {
                    const enabled = item.cats[cat.id] ?? false;
                    const key = `${item.id}:cat:${cat.id}`;
                    return (
                      <td key={cat.id} className="px-2 py-2 text-center">
                        <button
                          type="button"
                          onClick={() => onToggle(item, "cat", !enabled, cat.id)}
                          disabled={toggling === key}
                          className="disabled:opacity-50"
                        >
                          {enabled ? (
                            <ToggleRight size={18} className="text-blue-500" />
                          ) : (
                            <ToggleLeft size={18} className="text-gray-300 dark:text-gray-600" />
                          )}
                        </button>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
