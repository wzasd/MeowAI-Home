"use client";

import { useState } from "react";
import { Plus, Trash2, Power, PowerOff, Play, FileText, RefreshCw, Cpu } from "lucide-react";
import { useLimbs, type DeviceCapability, type DeviceStatus } from "../../hooks/useLimbs";

const CAPABILITY_LABELS: Record<DeviceCapability, string> = {
  actuator: "执行器",
  sensor: "传感器",
  display: "显示器",
  speaker: "扬声器",
  camera: "摄像头",
};

const STATUS_COLORS: Record<DeviceStatus, string> = {
  offline: "bg-gray-400",
  online: "bg-green-500",
  busy: "bg-yellow-500",
  error: "bg-red-500",
};

const STATUS_LABELS: Record<DeviceStatus, string> = {
  offline: "离线",
  online: "在线",
  busy: "忙碌",
  error: "错误",
};

export function LimbPanel() {
  const {
    devices,
    leases,
    loading,
    error,
    fetchDevices,
    fetchLeases,
    registerDevice,
    deleteDevice,
    pairDevice,
    unpairDevice,
    invokeDevice,
    getLogs,
    acquireLease,
    releaseLease,
  } = useLimbs();

  const [isAdding, setIsAdding] = useState(false);
  const [form, setForm] = useState({
    name: "",
    device_type: "",
    endpoint: "",
    capabilities: [] as DeviceCapability[],
  });
  const [expanded, setExpanded] = useState<string | null>(null);
  const [logsMap, setLogsMap] = useState<Record<string, Awaited<ReturnType<typeof getLogs>>>>({});
  const [invokeForm, setInvokeForm] = useState<Record<string, { action: string; params: string }>>({});
  const [invokeResult, setInvokeResult] = useState<Record<string, string>>({});

  const toggleCapability = (cap: DeviceCapability) => {
    setForm((prev) => ({
      ...prev,
      capabilities: prev.capabilities.includes(cap)
        ? prev.capabilities.filter((c) => c !== cap)
        : [...prev.capabilities, cap],
    }));
  };

  const handleAdd = async () => {
    if (!form.name || !form.device_type || !form.endpoint) return;
    await registerDevice(form);
    setForm({ name: "", device_type: "", endpoint: "", capabilities: [] });
    setIsAdding(false);
  };

  const toggleExpand = async (deviceId: string) => {
    if (expanded === deviceId) {
      setExpanded(null);
      return;
    }
    setExpanded(deviceId);
    const logs = await getLogs(deviceId, 20);
    setLogsMap((prev) => ({ ...prev, [deviceId]: logs }));
  };

  const doInvoke = async (deviceId: string) => {
    const action = invokeForm[deviceId]?.action?.trim();
    if (!action) return;
    let params = {};
    try {
      params = JSON.parse(invokeForm[deviceId]?.params || "{}");
    } catch {
      setInvokeResult((prev) => ({ ...prev, [deviceId]: "参数 JSON 格式错误" }));
      return;
    }
    const result = await invokeDevice(deviceId, action, params);
    setInvokeResult((prev) => ({
      ...prev,
      [deviceId]: result
        ? result.success
          ? `成功: ${JSON.stringify(result.result)}`
          : `失败: ${result.error || "未知错误"}`
        : "调用失败",
    }));
    const logs = await getLogs(deviceId, 20);
    setLogsMap((prev) => ({ ...prev, [deviceId]: logs }));
  };

  const deviceLease = (deviceId: string) => leases.find((l) => l.device_id === deviceId);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-gray-800 dark:text-gray-200">Limb 设备管理</h3>
        <div className="flex gap-2">
          <button
            onClick={() => {
              fetchDevices();
              fetchLeases();
            }}
            className="flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50 dark:border-gray-600 dark:hover:bg-gray-700"
          >
            <RefreshCw size={14} />
            刷新
          </button>
          <button
            onClick={() => setIsAdding(true)}
            className="flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700"
          >
            <Plus size={14} />
            注册设备
          </button>
        </div>
      </div>

      {error && <div className="rounded-lg bg-red-50 p-3 text-sm text-red-600 dark:bg-red-900/20">{error}</div>}

      {isAdding && (
        <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-900">
          <div className="grid gap-3 sm:grid-cols-2">
            <input
              value={form.name}
              onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
              placeholder="设备名称"
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
            />
            <input
              value={form.device_type}
              onChange={(e) => setForm((p) => ({ ...p, device_type: e.target.value }))}
              placeholder="设备类型 (如 smart_light)"
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
            />
            <input
              value={form.endpoint}
              onChange={(e) => setForm((p) => ({ ...p, endpoint: e.target.value }))}
              placeholder="Endpoint URL"
              className="sm:col-span-2 rounded-lg border border-gray-300 px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-800"
            />
            <div className="sm:col-span-2 flex flex-wrap gap-2">
              {(Object.keys(CAPABILITY_LABELS) as DeviceCapability[]).map((cap) => (
                <label key={cap} className="flex items-center gap-1 rounded-full border border-gray-300 px-2 py-1 text-xs dark:border-gray-600">
                  <input
                    type="checkbox"
                    checked={form.capabilities.includes(cap)}
                    onChange={() => toggleCapability(cap)}
                  />
                  {CAPABILITY_LABELS[cap]}
                </label>
              ))}
            </div>
          </div>
          <div className="mt-3 flex justify-end gap-2">
            <button
              onClick={() => setIsAdding(false)}
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-100 dark:border-gray-600"
            >
              取消
            </button>
            <button
              onClick={handleAdd}
              className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700"
            >
              保存
            </button>
          </div>
        </div>
      )}

      {loading && devices.length === 0 && <div className="text-sm text-gray-500">加载中...</div>}

      <div className="space-y-2">
        {devices.map((device) => {
          const lease = deviceLease(device.device_id);
          const isExpanded = expanded === device.device_id;
          return (
            <div
              key={device.device_id}
              className="rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800"
            >
              <div className="flex items-center justify-between px-4 py-3">
                <div className="flex items-center gap-3">
                  <Cpu size={18} className="text-gray-400" />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-800 dark:text-gray-200">{device.name}</span>
                      <span className={`h-2 w-2 rounded-full ${STATUS_COLORS[device.status]}`} />
                      <span className="text-xs text-gray-500">{STATUS_LABELS[device.status]}</span>
                      {device.is_paired ? (
                        <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700 dark:bg-green-900/30 dark:text-green-400">
                          已配对
                        </span>
                      ) : (
                        <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-gray-700 dark:text-gray-400">
                          未配对
                        </span>
                      )}
                    </div>
                    <div className="text-xs text-gray-500">
                      {device.device_type} · {device.endpoint}
                    </div>
                    <div className="mt-1 flex flex-wrap gap-1">
                      {device.capabilities.map((cap) => (
                        <span
                          key={cap}
                          className="rounded bg-blue-50 px-1.5 py-0.5 text-[10px] text-blue-600 dark:bg-blue-900/20 dark:text-blue-400"
                        >
                          {CAPABILITY_LABELS[cap] || cap}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {device.is_paired ? (
                    <button
                      onClick={() => unpairDevice(device.device_id)}
                      className="rounded-lg p-1.5 text-yellow-600 hover:bg-yellow-50 dark:text-yellow-400 dark:hover:bg-yellow-900/20"
                      title="取消配对"
                    >
                      <PowerOff size={16} />
                    </button>
                  ) : (
                    <button
                      onClick={() => pairDevice(device.device_id)}
                      className="rounded-lg p-1.5 text-green-600 hover:bg-green-50 dark:text-green-400 dark:hover:bg-green-900/20"
                      title="配对"
                    >
                      <Power size={16} />
                    </button>
                  )}
                  <button
                    onClick={() => toggleExpand(device.device_id)}
                    className="rounded-lg p-1.5 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
                    title="日志与调用"
                  >
                    <FileText size={16} />
                  </button>
                  <button
                    onClick={() => deleteDevice(device.device_id)}
                    className="rounded-lg p-1.5 text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
                    title="删除"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>

              {isExpanded && (
                <div className="border-t border-gray-200 px-4 py-3 dark:border-gray-700">
                  <div className="mb-3 flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">调用</span>
                    <input
                      value={invokeForm[device.device_id]?.action || ""}
                      onChange={(e) =>
                        setInvokeForm((prev) => ({
                          ...prev,
                          [device.device_id]: { ...(prev[device.device_id] || { params: "" }), action: e.target.value },
                        }))
                      }
                      placeholder="action"
                      className="w-32 rounded border border-gray-300 px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-800"
                    />
                    <input
                      value={invokeForm[device.device_id]?.params || ""}
                      onChange={(e) =>
                        setInvokeForm((prev) => ({
                          ...prev,
                          [device.device_id]: { ...(prev[device.device_id] || { action: "" }), params: e.target.value },
                        }))
                      }
                      placeholder='{"key":"value"}'
                      className="w-48 rounded border border-gray-300 px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-800"
                    />
                    <button
                      onClick={() => doInvoke(device.device_id)}
                      className="flex items-center gap-1 rounded bg-blue-600 px-2 py-1 text-xs text-white hover:bg-blue-700"
                    >
                      <Play size={12} />
                      执行
                    </button>
                    {invokeResult[device.device_id] && (
                      <span className="text-xs text-gray-600 dark:text-gray-400">
                        {invokeResult[device.device_id]}
                      </span>
                    )}
                  </div>

                  <div className="mb-3 flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">租约</span>
                    {lease ? (
                      <>
                        <span className="rounded bg-purple-100 px-2 py-0.5 text-xs text-purple-700 dark:bg-purple-900/20 dark:text-purple-400">
                          剩余 {Math.round(lease.remaining_seconds)}s
                        </span>
                        <button
                          onClick={() => releaseLease(device.device_id)}
                          className="rounded border border-gray-300 px-2 py-0.5 text-xs hover:bg-gray-50 dark:border-gray-600"
                        >
                          释放
                        </button>
                      </>
                    ) : (
                      <>
                        <span className="text-xs text-gray-500">无活跃租约</span>
                        <button
                          onClick={() => acquireLease(device.device_id, 300)}
                          className="rounded border border-gray-300 px-2 py-0.5 text-xs hover:bg-gray-50 dark:border-gray-600"
                        >
                          获取 (5min)
                        </button>
                      </>
                    )}
                  </div>

                  <div>
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">最近日志</span>
                    <div className="mt-1 max-h-40 overflow-y-auto rounded border border-gray-200 dark:border-gray-700">
                      {(logsMap[device.device_id] || []).length === 0 ? (
                        <div className="px-3 py-2 text-xs text-gray-500">暂无日志</div>
                      ) : (
                        <table className="w-full text-left text-xs">
                          <thead className="bg-gray-50 dark:bg-gray-900">
                            <tr>
                              <th className="px-3 py-1 font-medium text-gray-600 dark:text-gray-400">时间</th>
                              <th className="px-3 py-1 font-medium text-gray-600 dark:text-gray-400">动作</th>
                              <th className="px-3 py-1 font-medium text-gray-600 dark:text-gray-400">结果</th>
                            </tr>
                          </thead>
                          <tbody>
                            {(logsMap[device.device_id] || []).map((log) => (
                              <tr key={log.log_id} className="border-t border-gray-200 dark:border-gray-700">
                                <td className="px-3 py-1 text-gray-600 dark:text-gray-400">
                                  {new Date(log.timestamp * 1000).toLocaleTimeString()}
                                </td>
                                <td className="px-3 py-1">{log.action}</td>
                                <td className="px-3 py-1">
                                  {log.result.success ? (
                                    <span className="text-green-600">成功</span>
                                  ) : (
                                    <span className="text-red-600">失败</span>
                                  )}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {devices.length === 0 && !loading && (
        <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500 dark:border-gray-600">
          暂无 Limb 设备，点击右上角注册
        </div>
      )}
    </div>
  );
}
