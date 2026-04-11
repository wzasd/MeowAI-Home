import { useState, useEffect, useCallback } from "react";
import { api } from "../../api/client";
import {
  Check,
  AlertCircle,
  Loader2,
  TestTube,
  QrCode,
  Unplug,
  Link2,
  RefreshCw,
  ToggleLeft,
  ToggleRight,
} from "lucide-react";
import type { ConnectorResponse, ConnectorBindingStatus, ConnectorQrResponse } from "../../types";

const CONNECTOR_ICONS: Record<string, string> = {
  feishu: "🐦",
  dingtalk: "钉",
  weixin: "💬",
  wecom_bot: "🏢",
};

export function ConnectorSettings() {
  const [connectors, setConnectors] = useState<ConnectorResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [testing, setTesting] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string }>>({});
  const [configs, setConfigs] = useState<Record<string, Record<string, string>>>({});
  const [bindingStatus, setBindingStatus] = useState<Record<string, ConnectorBindingStatus>>({});
  const [qrData, setQrData] = useState<Record<string, ConnectorQrResponse>>({});
  const [qrLoading, setQrLoading] = useState<string | null>(null);
  const [showQr, setShowQr] = useState<string | null>(null);

  useEffect(() => {
    fetchConnectors();
  }, []);

  const fetchConnectors = async () => {
    try {
      const data = await api.connectors.list();
      setConnectors(data.connectors);
      // Fetch binding status for each connector
      for (const c of data.connectors) {
        fetchBindingStatus(c.name);
      }
    } catch (error) {
      console.error("Failed to fetch connectors:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchBindingStatus = async (name: string) => {
    try {
      const status = await api.connectors.getBindingStatus(name);
      setBindingStatus((prev) => ({ ...prev, [name]: status }));
    } catch {
      // Binding status not available, that's OK
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

  const handleShowQr = async (name: string) => {
    if (showQr === name) {
      setShowQr(null);
      return;
    }
    setQrLoading(name);
    try {
      const qr = await api.connectors.getQr(name);
      setQrData((prev) => ({ ...prev, [name]: qr }));
      setShowQr(name);
    } catch (error) {
      console.error("Failed to get QR:", error);
    } finally {
      setQrLoading(null);
    }
  };

  const handleSimulateBind = async (name: string) => {
    const qr = qrData[name];
    if (!qr) return;
    try {
      await api.connectors.bindCallback(name, qr.token, "MeowAI 用户");
      await fetchBindingStatus(name);
      setShowQr(null);
    } catch (error) {
      console.error("Bind failed:", error);
    }
  };

  const handleUnbind = async (name: string) => {
    try {
      await api.connectors.unbind(name);
      await fetchBindingStatus(name);
    } catch (error) {
      console.error("Unbind failed:", error);
    }
  };

  const handleToggleEnabled = async (name: string, currentlyEnabled: boolean) => {
    try {
      if (currentlyEnabled) {
        await api.connectors.disable(name);
      } else {
        await api.connectors.enable(name);
      }
      await fetchConnectors();
    } catch (error) {
      console.error("Toggle failed:", error);
    }
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

      {connectors.map((connector) => {
        const binding = bindingStatus[connector.name];
        const isQrVisible = showQr === connector.name;
        const qr = qrData[connector.name];
        const icon = CONNECTOR_ICONS[connector.name] || "🔗";

        return (
          <div
            key={connector.name}
            className="rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
          >
            {/* Header */}
            <div className="flex items-start justify-between p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100 text-lg dark:bg-gray-700">
                  {icon}
                </div>
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
                    {binding?.bound && (
                      <span className="flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                        <Link2 size={10} />
                        已绑定 {binding.bound_user}
                      </span>
                    )}
                  </div>
                  <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">
                    支持: {connector.features.join(", ")}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {/* Test result */}
                {testResults[connector.name] && (
                  <div
                    className={`flex items-center gap-1 text-xs ${
                      testResults[connector.name]?.success
                        ? "text-green-600 dark:text-green-400"
                        : "text-red-600 dark:text-red-400"
                    }`}
                  >
                    {testResults[connector.name]?.success ? (
                      <Check size={14} />
                    ) : (
                      <AlertCircle size={14} />
                    )}
                    {testResults[connector.name]?.success ? "连接成功" : "连接失败"}
                  </div>
                )}

                {/* Enable/disable toggle */}
                <button
                  onClick={() => handleToggleEnabled(connector.name, connector.enabled)}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  title={connector.enabled ? "禁用" : "启用"}
                >
                  {connector.enabled ? (
                    <ToggleRight size={24} className="text-green-500" />
                  ) : (
                    <ToggleLeft size={24} />
                  )}
                </button>
              </div>
            </div>

            {/* Binding actions */}
            {connector.enabled && (
              <div className="flex items-center gap-2 border-t border-gray-100 px-4 py-2 dark:border-gray-700">
                {binding?.bound ? (
                  <>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      绑定时间:{" "}
                      {binding.bound_at
                        ? new Date(binding.bound_at).toLocaleString("zh-CN")
                        : "—"}
                    </span>
                    <button
                      onClick={() => handleUnbind(connector.name)}
                      className="flex items-center gap-1 rounded px-2 py-1 text-xs text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
                    >
                      <Unplug size={12} />
                      解除绑定
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={() => handleShowQr(connector.name)}
                      disabled={qrLoading === connector.name}
                      className="flex items-center gap-1 rounded bg-blue-50 px-2 py-1 text-xs text-blue-600 hover:bg-blue-100 disabled:opacity-50 dark:bg-blue-900/30 dark:text-blue-400"
                    >
                      {qrLoading === connector.name ? (
                        <Loader2 size={12} className="animate-spin" />
                      ) : (
                        <QrCode size={12} />
                      )}
                      {isQrVisible ? "收起二维码" : "扫码绑定"}
                    </button>
                    <button
                      onClick={() => handleSimulateBind(connector.name)}
                      disabled={!qr}
                      className="flex items-center gap-1 rounded bg-green-50 px-2 py-1 text-xs text-green-600 hover:bg-green-100 disabled:opacity-50 dark:bg-green-900/30 dark:text-green-400"
                      title="模拟用户扫码成功（测试用）"
                    >
                      <Link2 size={12} />
                      模拟绑定
                    </button>
                  </>
                )}
              </div>
            )}

            {/* QR display area */}
            {isQrVisible && qr && (
              <div className="flex items-center justify-center border-t border-gray-100 bg-gray-50 px-4 py-4 dark:border-gray-700 dark:bg-gray-900">
                <div className="text-center">
                  <img
                    src={qr.qr_data_url}
                    alt="QR Code"
                    className="mx-auto h-[180px] w-[180px]"
                  />
                  <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                    扫描二维码绑定 {connector.displayName}
                  </p>
                  <p className="text-[10px] text-gray-400 dark:text-gray-500">
                    有效期 {qr.expires_in / 60} 分钟
                  </p>
                </div>
              </div>
            )}

            {/* Config fields */}
            {connector.configFields.length > 0 && (
              <div className="space-y-3 border-t border-gray-100 p-4 dark:border-gray-700">
                <p className="text-xs font-medium text-gray-500 dark:text-gray-400">配置参数</p>
                {connector.configFields.map((field) => (
                  <div key={field}>
                    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300">
                      {field}
                    </label>
                    <input
                      type={field.includes("secret") || field.includes("key") ? "password" : "text"}
                      value={configs[connector.name]?.[field] || ""}
                      onChange={(e) => updateConfig(connector.name, field, e.target.value)}
                      placeholder={`输入 ${field}`}
                      className="mt-1 w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
                    />
                  </div>
                ))}

                <div className="flex gap-2">
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
                  <button
                    onClick={fetchConnectors}
                    className="flex items-center gap-1 rounded-md px-3 py-1.5 text-sm text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700"
                  >
                    <RefreshCw size={14} />
                    刷新
                  </button>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
