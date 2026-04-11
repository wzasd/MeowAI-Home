import { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Check, AlertCircle, Loader2, TestTube } from "lucide-react";

interface Connector {
  name: string;
  displayName: string;
  enabled: boolean;
  status: string;
  features: string[];
  configFields: string[];
}

export function ConnectorSettings() {
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string }>>({});
  const [configs, setConfigs] = useState<Record<string, Record<string, string>>>({});

  useEffect(() => {
    fetchConnectors();
  }, []);

  const fetchConnectors = async () => {
    try {
      const data = await api.connectors.list();
      setConnectors(data.connectors);
    } catch (error) {
      console.error("Failed to fetch connectors:", error);
    } finally {
      setLoading(false);
    }
  };

  const testConnector = async (name: string) => {
    setTesting(name);
    try {
      const result = await api.connectors.test(name, configs[name] || {});
      setTestResults((prev) => ({ ...prev, [name]: result }));
    } catch (error) {
      setTestResults((prev) => ({
        ...prev,
        [name]: { success: false, message: String(error) },
      }));
    } finally {
      setTesting(null);
    }
  };

  const updateConfig = (connectorName: string, field: string, value: string) => {
    setConfigs((prev) => ({
      ...prev,
      [connectorName]: { ...(prev[connectorName] || {}), [field]: value },
    }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="text-sm text-gray-600 dark:text-gray-400">
        配置与外部平台的连接。启用后，您可以通过这些平台与 MeowAI 交互。
      </div>

      {connectors.map((connector) => (
        <div
          key={connector.name}
          className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
        >
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <h4 className="font-medium text-gray-900 dark:text-gray-100">
                  {connector.displayName}
                </h4>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs ${
                    connector.enabled
                      ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                      : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400"
                  }`}
                >
                  {connector.enabled ? "已启用" : "未启用"}
                </span>
              </div>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                支持: {connector.features.join(", ")}
              </p>
            </div>

            {testResults[connector.name] && (
              <div
                className={`flex items-center gap-1 text-sm ${
                  testResults[connector.name]?.success
                    ? "text-green-600 dark:text-green-400"
                    : "text-red-600 dark:text-red-400"
                }`}
              >
                {testResults[connector.name]?.success ? (
                  <Check size={16} />
                ) : (
                  <AlertCircle size={16} />
                )}
                {testResults[connector.name]?.success ? "连接成功" : "连接失败"}
              </div>
            )}
          </div>

          {/* Config Fields */}
          <div className="mt-4 space-y-3">
            {connector.configFields.map((field) => (
              <div key={field}>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
                  {field}
                </label>
                <input
                  type="text"
                  value={configs[connector.name]?.[field] || ""}
                  onChange={(e) => updateConfig(connector.name, field, e.target.value)}
                  placeholder={`输入 ${field}`}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
                />
              </div>
            ))}
          </div>

          {/* Actions */}
          <div className="mt-4 flex gap-2">
            <button
              onClick={() => testConnector(connector.name)}
              disabled={testing === connector.name}
              className="flex items-center gap-1 rounded-md bg-blue-50 px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-100 disabled:opacity-50 dark:bg-blue-900/30 dark:text-blue-400"
            >
              {testing === connector.name ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <TestTube size={14} />
              )}
              测试连接
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
