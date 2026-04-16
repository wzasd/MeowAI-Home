"use client";

import { useCallback, useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "";

export type DeviceStatus = "offline" | "online" | "busy" | "error";
export type DeviceCapability = "actuator" | "sensor" | "display" | "speaker" | "camera";

export interface LimbDevice {
  device_id: string;
  name: string;
  device_type: string;
  capabilities: DeviceCapability[];
  status: DeviceStatus;
  endpoint: string;
  metadata: Record<string, unknown>;
  owner_user_id?: string;
  registered_at: number;
  last_seen_at?: number;
  health_check_interval: number;
  is_paired: boolean;
  is_available: boolean;
}

export interface Lease {
  lease_id: string;
  user_id: string;
  device_id: string;
  acquired_at: number;
  expires_at: number;
  remaining_seconds: number;
}

export interface InvocationLog {
  log_id: string;
  device_id: string;
  user_id: string;
  action: string;
  params: Record<string, unknown>;
  result: {
    success: boolean;
    device_id: string;
    action: string;
    result?: unknown;
    error?: string;
    execution_time_ms: number;
    timestamp: number;
  };
  timestamp: number;
}

export interface InvokeResult {
  success: boolean;
  device_id: string;
  action: string;
  result?: unknown;
  error?: string;
  execution_time_ms: number;
  timestamp: number;
}

interface UseLimbsReturn {
  devices: LimbDevice[];
  availableDevices: LimbDevice[];
  leases: Lease[];
  loading: boolean;
  error: string | null;
  fetchDevices: () => Promise<void>;
  fetchAvailable: () => Promise<void>;
  fetchLeases: () => Promise<void>;
  registerDevice: (data: {
    name: string;
    device_type: string;
    endpoint: string;
    capabilities?: DeviceCapability[];
    auth_token?: string;
    owner_user_id?: string;
    metadata?: Record<string, unknown>;
  }) => Promise<LimbDevice | null>;
  updateDevice: (deviceId: string, data: {
    name?: string;
    endpoint?: string;
    status?: DeviceStatus;
    auth_token?: string;
    metadata?: Record<string, unknown>;
  }) => Promise<boolean>;
  deleteDevice: (deviceId: string) => Promise<boolean>;
  pairDevice: (deviceId: string) => Promise<boolean>;
  unpairDevice: (deviceId: string) => Promise<boolean>;
  invokeDevice: (deviceId: string, action: string, params?: Record<string, unknown>) => Promise<InvokeResult | null>;
  getLogs: (deviceId: string, limit?: number) => Promise<InvocationLog[]>;
  acquireLease: (deviceId: string, ttlSeconds?: number) => Promise<boolean>;
  releaseLease: (deviceId: string) => Promise<boolean>;
  extendLease: (deviceId: string, additionalSeconds?: number) => Promise<boolean>;
}

export function useLimbs(): UseLimbsReturn {
  const [devices, setDevices] = useState<LimbDevice[]>([]);
  const [availableDevices, setAvailableDevices] = useState<LimbDevice[]>([]);
  const [leases, setLeases] = useState<Lease[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDevices = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/limbs`);
      if (!res.ok) throw new Error(`Failed to fetch devices: ${res.status}`);
      const data = await res.json();
      setDevices(data.devices || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch devices");
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchAvailable = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/limbs/available`);
      if (!res.ok) throw new Error(`Failed to fetch available devices: ${res.status}`);
      const data = await res.json();
      setAvailableDevices(data.devices || []);
    } catch (err) {
      console.error("Failed to fetch available devices:", err);
    }
  }, []);

  const fetchLeases = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/limbs/leases`);
      if (!res.ok) throw new Error(`Failed to fetch leases: ${res.status}`);
      const data = await res.json();
      setLeases(data.leases || []);
    } catch (err) {
      console.error("Failed to fetch leases:", err);
    }
  }, []);

  const registerDevice = useCallback(async (data: {
    name: string;
    device_type: string;
    endpoint: string;
    capabilities?: DeviceCapability[];
    auth_token?: string;
    owner_user_id?: string;
    metadata?: Record<string, unknown>;
  }) => {
    try {
      const res = await fetch(`${API_BASE}/api/limbs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!res.ok) return null;
      const json = await res.json();
      const device = json.device as LimbDevice;
      setDevices((prev) => [...prev, device]);
      return device;
    } catch {
      return null;
    }
  }, []);

  const updateDevice = useCallback(async (deviceId: string, data: {
    name?: string;
    endpoint?: string;
    status?: DeviceStatus;
    auth_token?: string;
    metadata?: Record<string, unknown>;
  }) => {
    try {
      const res = await fetch(`${API_BASE}/api/limbs/${deviceId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      if (!res.ok) return false;
      const json = await res.json();
      const device = json.device as LimbDevice;
      setDevices((prev) => prev.map((d) => (d.device_id === deviceId ? device : d)));
      setAvailableDevices((prev) => {
        const exists = prev.some((d) => d.device_id === deviceId);
        if (device.is_available && !exists) return [...prev, device];
        if (!device.is_available && exists) return prev.filter((d) => d.device_id !== deviceId);
        return prev.map((d) => (d.device_id === deviceId ? device : d));
      });
      return true;
    } catch {
      return false;
    }
  }, []);

  const deleteDevice = useCallback(async (deviceId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/limbs/${deviceId}`, { method: "DELETE" });
      if (!res.ok) return false;
      setDevices((prev) => prev.filter((d) => d.device_id !== deviceId));
      setAvailableDevices((prev) => prev.filter((d) => d.device_id !== deviceId));
      return true;
    } catch {
      return false;
    }
  }, []);

  const pairDevice = useCallback(async (deviceId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/limbs/${deviceId}/pair`, { method: "POST" });
      if (!res.ok) return false;
      const json = await res.json();
      const device = json.device as LimbDevice;
      setDevices((prev) => prev.map((d) => (d.device_id === deviceId ? device : d)));
      if (device.is_available) {
        setAvailableDevices((prev) => {
          if (prev.some((d) => d.device_id === deviceId)) return prev;
          return [...prev, device];
        });
      }
      return true;
    } catch {
      return false;
    }
  }, []);

  const unpairDevice = useCallback(async (deviceId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/limbs/${deviceId}/unpair`, { method: "POST" });
      if (!res.ok) return false;
      const json = await res.json();
      const device = json.device as LimbDevice;
      setDevices((prev) => prev.map((d) => (d.device_id === deviceId ? device : d)));
      setAvailableDevices((prev) => prev.filter((d) => d.device_id !== deviceId));
      return true;
    } catch {
      return false;
    }
  }, []);

  const invokeDevice = useCallback(async (deviceId: string, action: string, params?: Record<string, unknown>) => {
    try {
      const res = await fetch(`${API_BASE}/api/limbs/${deviceId}/invoke`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, params: params || {} }),
      });
      if (!res.ok) return null;
      return (await res.json()) as InvokeResult;
    } catch {
      return null;
    }
  }, []);

  const getLogs = useCallback(async (deviceId: string, limit = 100) => {
    try {
      const res = await fetch(`${API_BASE}/api/limbs/${deviceId}/logs?limit=${limit}`);
      if (!res.ok) return [];
      const data = await res.json();
      return (data.logs || []) as InvocationLog[];
    } catch {
      return [];
    }
  }, []);

  const acquireLease = useCallback(async (deviceId: string, ttlSeconds?: number) => {
    try {
      const res = await fetch(`${API_BASE}/api/limbs/leases/${deviceId}/acquire`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ttl_seconds: ttlSeconds }),
      });
      if (!res.ok) return false;
      await fetchLeases();
      return true;
    } catch {
      return false;
    }
  }, [fetchLeases]);

  const releaseLease = useCallback(async (deviceId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/limbs/leases/${deviceId}/release`, { method: "POST" });
      if (!res.ok) return false;
      await fetchLeases();
      return true;
    } catch {
      return false;
    }
  }, [fetchLeases]);

  const extendLease = useCallback(async (deviceId: string, additionalSeconds = 300) => {
    try {
      const res = await fetch(`${API_BASE}/api/limbs/leases/${deviceId}/extend`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ additional_seconds: additionalSeconds }),
      });
      if (!res.ok) return false;
      await fetchLeases();
      return true;
    } catch {
      return false;
    }
  }, [fetchLeases]);

  useEffect(() => {
    fetchDevices();
    fetchAvailable();
    fetchLeases();
  }, [fetchDevices, fetchAvailable, fetchLeases]);

  return {
    devices,
    availableDevices,
    leases,
    loading,
    error,
    fetchDevices,
    fetchAvailable,
    fetchLeases,
    registerDevice,
    updateDevice,
    deleteDevice,
    pairDevice,
    unpairDevice,
    invokeDevice,
    getLogs,
    acquireLease,
    releaseLease,
    extendLease,
  };
}
