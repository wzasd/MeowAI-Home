import { useCatStore } from "../../stores/catStore";
import { Shield, Check, X } from "lucide-react";

interface Permission {
  id: string;
  name: string;
  description: string;
  riskLevel: "low" | "medium" | "high";
}

const PERMISSIONS: Permission[] = [
  { id: "write_file", name: "写入文件", description: "允许创建和修改文件", riskLevel: "medium" },
  { id: "execute_command", name: "执行命令", description: "允许运行 Shell 命令", riskLevel: "high" },
  { id: "network_access", name: "网络访问", description: "允许发起 HTTP 请求", riskLevel: "medium" },
  { id: "read_all_threads", name: "读取所有线程", description: "允许访问其他线程的对话内容", riskLevel: "low" },
  { id: "manage_cats", name: "管理猫咪", description: "允许创建/修改/删除猫咪配置", riskLevel: "high" },
  { id: "send_notification", name: "发送通知", description: "允许发送推送通知", riskLevel: "low" },
  { id: "access_environment", name: "访问环境变量", description: "允许读取和修改环境变量", riskLevel: "high" },
  { id: "invoke_other_cats", name: "调用其他猫", description: "允许通过 A2A 调用其他 Agent", riskLevel: "medium" },
];

const RISK_COLORS = {
  low: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  medium: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  high: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
};

export function PermissionsSettings() {
  const cats = useCatStore((s) => s.cats);

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600 dark:text-gray-400">
        配置每只猫咪的权限范围。高风险操作需要显式授权。
      </p>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200 text-xs text-gray-500 dark:border-gray-700">
              <th className="px-3 py-2 text-left">权限</th>
              <th className="px-3 py-2 text-left">风险</th>
              {cats.slice(0, 5).map((cat) => (
                <th key={cat.id} className="px-3 py-2 text-center">
                  <span className="text-xs font-medium text-gray-700 dark:text-gray-300">{cat.displayName || cat.name}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {PERMISSIONS.map((perm) => (
              <tr key={perm.id} className="border-b border-gray-100 last:border-0 dark:border-gray-700/50">
                <td className="px-3 py-2">
                  <div>
                    <span className="text-sm text-gray-800 dark:text-gray-200">{perm.name}</span>
                    <p className="text-[10px] text-gray-400">{perm.description}</p>
                  </div>
                </td>
                <td className="px-3 py-2">
                  <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${RISK_COLORS[perm.riskLevel]}`}>
                    {perm.riskLevel === "low" ? "低" : perm.riskLevel === "medium" ? "中" : "高"}
                  </span>
                </td>
                {cats.slice(0, 5).map((cat) => {
                  // Default: low risk = enabled, medium = enabled, high = disabled
                  const enabled = perm.riskLevel !== "high";
                  return (
                    <td key={cat.id} className="px-3 py-2 text-center">
                      <button
                        className={`rounded p-1 ${enabled ? "text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20" : "text-gray-300 hover:bg-gray-100 dark:text-gray-600 dark:hover:bg-gray-700"}`}
                      >
                        {enabled ? <Check size={16} /> : <X size={16} />}
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Risk legend */}
      <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
        <span className="flex items-center gap-1">
          <Shield size={12} /> 权限说明
        </span>
        <span className={RISK_COLORS.low + " rounded px-1.5 py-0.5"}>低风险 — 默认允许</span>
        <span className={RISK_COLORS.medium + " rounded px-1.5 py-0.5"}>中风险 — 默认允许</span>
        <span className={RISK_COLORS.high + " rounded px-1.5 py-0.5"}>高风险 — 需要授权</span>
      </div>
    </div>
  );
}
