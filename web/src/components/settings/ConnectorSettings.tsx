import { useCallback, useEffect, useState } from "react";
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
import type { ConnectorBindingStatus, ConnectorQrResponse, ConnectorResponse } from "../../types";
import { SettingsSectionCard, SettingsSummaryGrid } from "./SettingsSectionCard";
import { buildConnectorSummaryCards } from "./settingsSummaryModels";

const CONNECTOR_ICONS: Record<string, string> = {
  feishu: "🐦",
  dingtalk: "钉",
  weixin: "💬",
  wecom_bot: "🏢",
};

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

export function ConnectorSettings() {
  const [connectors, setConnectors] = useState<ConnectorResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [testing, setTesting] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<
    Record<string, { success: boolean; message: string }>
  >({});
  const [configs, setConfigs] = useState<Record<string, Record<string, string>>>({});
  const [bindingStatus, setBindingStatus] = useState<Record<string, ConnectorBindingStatus>>({});
  const [qrData, setQrData] = useState<Record<string, ConnectorQrResponse>>({});
  const [qrLoading, setQrLoading] = useState<string | null>(null);
  const [showQr, setShowQr] = useState<string | null>(null);

  const fetchBindingStatus = useCallback(
    async (name: string): Promise<ConnectorBindingStatus | null> => {
      try {
        return await api.connectors.getBindingStatus(name);
      } catch {
        return null;
      }
    },
    []
  );

  const fetchConnectors = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.connectors.list();
      setConnectors(data.connectors);

      const statuses = await Promise.all(
        data.connectors.map(async (connector) => {
          const status = await fetchBindingStatus(connector.name);
          return [connector.name, status] as const;
        })
      );

      setBindingStatus(
        Object.fromEntries(
          statuses.flatMap(([name, status]) => (status ? [[name, status]] : []))
        ) as Record<string, ConnectorBindingStatus>
      );
    } catch (error) {
      setError(getErrorMessage(error, "加载连接器失败"));
    } finally {
      setLoading(false);
    }
  }, [fetchBindingStatus]);

  useEffect(() => {
    void fetchConnectors();
  }, [fetchConnectors]);

  const testConnector = async (name: string) => {
    setTesting(name);
    setError(null);
    try {
      const result = await api.connectors.test(name, configs[name] || {});
      setTestResults((prev) => ({ ...prev, [name]: result }));
    } catch (error) {
      const message = getErrorMessage(error, "连接测试失败");
      setTestResults((prev) => ({
        ...prev,
        [name]: { success: false, message },
      }));
      setError(message);
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
    setError(null);
    try {
      const qr = await api.connectors.getQr(name);
      setQrData((prev) => ({ ...prev, [name]: qr }));
      setShowQr(name);
    } catch (error) {
      setError(getErrorMessage(error, "获取二维码失败"));
    } finally {
      setQrLoading(null);
    }
  };

  const handleSimulateBind = async (name: string) => {
    const qr = qrData[name];
    if (!qr) return;
    setError(null);
    try {
      await api.connectors.bindCallback(name, qr.token, "MeowAI 用户");
      const status = await fetchBindingStatus(name);
      if (status) {
        setBindingStatus((prev) => ({ ...prev, [name]: status }));
      }
      setShowQr(null);
    } catch (error) {
      setError(getErrorMessage(error, "绑定失败"));
    }
  };

  const handleUnbind = async (name: string) => {
    setError(null);
    try {
      await api.connectors.unbind(name);
      const status = await fetchBindingStatus(name);
      if (status) {
        setBindingStatus((prev) => ({ ...prev, [name]: status }));
      } else {
        setBindingStatus((prev) => {
          const next = { ...prev };
          delete next[name];
          return next;
        });
      }
    } catch (error) {
      setError(getErrorMessage(error, "解除绑定失败"));
    }
  };

  const handleToggleEnabled = async (name: string, currentlyEnabled: boolean) => {
    setError(null);
    try {
      if (currentlyEnabled) {
        await api.connectors.disable(name);
      } else {
        await api.connectors.enable(name);
      }
      await fetchConnectors();
    } catch (error) {
      setError(getErrorMessage(error, currentlyEnabled ? "禁用失败" : "启用失败"));
    }
  };

  if (loading && connectors.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-[var(--accent)]" />
      </div>
    );
  }

  const summaryCards = buildConnectorSummaryCards(connectors, bindingStatus);

  return (
    <div className="space-y-5">
      <SettingsSummaryGrid items={summaryCards} />

      <SettingsSectionCard
        eyebrow="Connector Fabric"
        title="外部通道编排"
        description="先确认哪些通道已经启用、哪些已经绑定，再继续做二维码绑定、配置测试和启停操作。"
        actions={
          <button
            type="button"
            onClick={() => void fetchConnectors()}
            className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-white/65 px-3 py-2 text-sm text-[var(--text-soft)] transition-colors hover:border-[var(--border-strong)] hover:text-[var(--text-strong)] dark:bg-white/[0.05]"
          >
            <RefreshCw size={14} />
            刷新通道
          </button>
        }
      >
        <div className="space-y-4">
          {error && (
            <div className="rounded-[1rem] border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-500 dark:border-red-900/40 dark:bg-red-900/20 dark:text-red-400">
              {error}
            </div>
          )}

          {connectors.length === 0 ? (
            <div className="rounded-[1.25rem] border border-dashed border-[var(--border)] bg-white/45 px-5 py-10 text-center dark:bg-white/[0.03]">
              <div className="text-sm font-medium text-[var(--text-strong)]">
                当前没有可用连接器
              </div>
              <p className="mt-2 text-sm leading-7 text-[var(--text-soft)]">
                先确认后端是否暴露了连接器能力，再回来做启用、绑定和配置测试。
              </p>
            </div>
          ) : (
            <div className="grid gap-4">
              {connectors.map((connector) => {
                const binding = bindingStatus[connector.name];
                const isQrVisible = showQr === connector.name;
                const qr = qrData[connector.name];
                const icon = CONNECTOR_ICONS[connector.name] || "🔗";

                return (
                  <div
                    key={connector.name}
                    className="rounded-[1.25rem] border border-[var(--border)] bg-white/70 shadow-[0_18px_40px_-28px_rgba(15,23,42,0.45)] dark:bg-white/[0.04]"
                  >
                    <div className="flex items-start justify-between p-4">
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[var(--accent-soft)] text-lg text-[var(--accent-deep)] dark:text-[var(--accent)]">
                          {icon}
                        </div>
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <h4 className="font-medium text-[var(--text-strong)]">
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
                              <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                                <Link2 size={10} />
                                已绑定 {binding.bound_user}
                              </span>
                            )}
                          </div>
                          <p className="mt-1 text-xs text-[var(--text-faint)]">
                            支持能力：{connector.features.join("、")}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        {testResults[connector.name] && (
                          <div
                            className={`flex items-center gap-1 text-xs ${
                              testResults[connector.name]?.success
                                ? "text-green-600 dark:text-green-400"
                                : "text-red-600 dark:text-red-400"
                            }`}
                            title={testResults[connector.name]?.message}
                          >
                            {testResults[connector.name]?.success ? (
                              <Check size={14} />
                            ) : (
                              <AlertCircle size={14} />
                            )}
                            {testResults[connector.name]?.success ? "连接成功" : "连接失败"}
                          </div>
                        )}
                        <button
                          onClick={() =>
                            void handleToggleEnabled(connector.name, connector.enabled)
                          }
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

                    {connector.enabled && (
                      <div className="flex flex-wrap items-center gap-2 border-t border-[var(--line)] px-4 py-3">
                        {binding?.bound ? (
                          <>
                            <span className="text-xs text-[var(--text-faint)]">
                              绑定时间：
                              {binding.bound_at
                                ? new Date(binding.bound_at).toLocaleString("zh-CN")
                                : "—"}
                            </span>
                            <button
                              onClick={() => void handleUnbind(connector.name)}
                              className="inline-flex items-center gap-1 rounded-full bg-red-50 px-3 py-1.5 text-xs text-red-600 hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400"
                            >
                              <Unplug size={12} />
                              解除绑定
                            </button>
                          </>
                        ) : (
                          <>
                            <button
                              onClick={() => void handleShowQr(connector.name)}
                              disabled={qrLoading === connector.name}
                              className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-3 py-1.5 text-xs text-blue-600 hover:bg-blue-100 disabled:opacity-50 dark:bg-blue-900/30 dark:text-blue-400"
                            >
                              {qrLoading === connector.name ? (
                                <Loader2 size={12} className="animate-spin" />
                              ) : (
                                <QrCode size={12} />
                              )}
                              {isQrVisible ? "收起二维码" : "扫码绑定"}
                            </button>
                            {connector.name === "feishu" && qr && (
                              <button
                                onClick={() => void handleSimulateBind(connector.name)}
                                disabled={!qr}
                                className="inline-flex items-center gap-1 rounded-full bg-green-50 px-3 py-1.5 text-xs text-green-600 hover:bg-green-100 disabled:opacity-50 dark:bg-green-900/30 dark:text-green-400"
                                title="模拟用户扫码成功（测试用）"
                              >
                                <Link2 size={12} />
                                模拟绑定
                              </button>
                            )}
                          </>
                        )}
                      </div>
                    )}

                    {isQrVisible && qr && (
                      <div className="flex items-center justify-center border-t border-[var(--line)] bg-[rgba(20,16,13,0.03)] px-4 py-4 dark:bg-white/[0.02]">
                        <div className="text-center">
                          <img
                            src={qr.qr_data_url}
                            alt="QR Code"
                            className="mx-auto h-[180px] w-[180px]"
                          />
                          <p className="mt-2 text-xs text-[var(--text-soft)]">
                            扫描二维码绑定 {connector.displayName}
                          </p>
                          <p className="text-[10px] text-[var(--text-faint)]">
                            有效期 {qr.expires_in / 60} 分钟
                          </p>
                        </div>
                      </div>
                    )}

                    {connector.configFields.length > 0 && (
                      <div className="space-y-3 border-t border-[var(--line)] p-4">
                        <p className="text-xs font-medium text-[var(--text-faint)]">配置参数</p>
                        {connector.configFields.map((field) => (
                          <div key={field}>
                            <label className="block text-xs font-medium text-[var(--text-soft)]">
                              {field}
                            </label>
                            <input
                              type={
                                field.includes("secret") || field.includes("key")
                                  ? "password"
                                  : "text"
                              }
                              value={configs[connector.name]?.[field] || ""}
                              onChange={(e) => updateConfig(connector.name, field, e.target.value)}
                              placeholder={`输入 ${field}`}
                              className="mt-1 w-full rounded-xl border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
                            />
                          </div>
                        ))}

                        <div className="flex flex-wrap gap-2">
                          <button
                            onClick={() => void testConnector(connector.name)}
                            disabled={testing === connector.name}
                            className="inline-flex items-center gap-1 rounded-xl bg-blue-50 px-3 py-2 text-sm text-blue-600 hover:bg-blue-100 disabled:opacity-50 dark:bg-blue-900/30 dark:text-blue-400"
                          >
                            {testing === connector.name ? (
                              <Loader2 size={14} className="animate-spin" />
                            ) : (
                              <TestTube size={14} />
                            )}
                            测试连接
                          </button>
                          <button
                            onClick={() => void fetchConnectors()}
                            className="inline-flex items-center gap-1 rounded-xl px-3 py-2 text-sm text-[var(--text-soft)] hover:bg-white/50 dark:hover:bg-white/[0.06]"
                          >
                            <RefreshCw size={14} />
                            刷新状态
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </SettingsSectionCard>
    </div>
  );
}
