/** Connector messages hook — fetch and manage external system messages. */

import { useState, useEffect, useCallback, useRef } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "";
const WS_BASE = API_BASE.replace(/^http/, "ws") || `ws://${window.location.host}`;

export type ConnectorType = "feishu" | "dingtalk" | "weixin" | "wecom" | "github" | "scheduler" | "system";
export type ContentBlockType = "text" | "image" | "file";

export interface ContentBlock {
  type: ContentBlockType;
  text?: string;
  url?: string;
  mime_type?: string;
}

export interface SenderInfo {
  id: string;
  name: string;
  avatar?: string;
}

export interface ConnectorMessage {
  id: string;
  connector: ConnectorType;
  connector_type: "group" | "private" | "system";
  sender: SenderInfo;
  content: string;
  content_blocks: ContentBlock[];
  timestamp: number;
  source_url?: string;
  icon: string;
  thread_id?: string;
}

export interface ConnectorTheme {
  avatar: string;
  label: string;
  bubble: string;
}

const CONNECTOR_THEMES: Record<ConnectorType, ConnectorTheme> = {
  feishu: {
    avatar: "bg-blue-100 ring-2 ring-blue-200",
    label: "text-blue-700",
    bubble: "border border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20",
  },
  dingtalk: {
    avatar: "bg-cyan-100 ring-2 ring-cyan-200",
    label: "text-cyan-700",
    bubble: "border border-cyan-200 bg-cyan-50 dark:border-cyan-800 dark:bg-cyan-900/20",
  },
  weixin: {
    avatar: "bg-green-100 ring-2 ring-green-200",
    label: "text-green-700",
    bubble: "border border-green-200 bg-green-50 dark:border-green-800 dark:bg-green-900/20",
  },
  wecom: {
    avatar: "bg-indigo-100 ring-2 ring-indigo-200",
    label: "text-indigo-700",
    bubble: "border border-indigo-200 bg-indigo-50 dark:border-indigo-800 dark:bg-indigo-900/20",
  },
  github: {
    avatar: "bg-gray-100 ring-2 ring-gray-200 dark:bg-gray-700 dark:ring-gray-600",
    label: "text-gray-700 dark:text-gray-300",
    bubble: "border border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800/50",
  },
  scheduler: {
    avatar: "bg-amber-100 ring-2 ring-amber-200",
    label: "text-amber-700",
    bubble: "border border-amber-200 bg-amber-50 dark:border-amber-800 dark:bg-amber-900/20",
  },
  system: {
    avatar: "bg-purple-100 ring-2 ring-purple-200",
    label: "text-purple-700",
    bubble: "border border-purple-200 bg-purple-50 dark:border-purple-800 dark:bg-purple-900/20",
  },
};

const CONNECTOR_LABELS: Record<ConnectorType, string> = {
  feishu: "飞书",
  dingtalk: "钉钉",
  weixin: "微信",
  wecom: "企业微信",
  github: "GitHub",
  scheduler: "定时任务",
  system: "系统",
};

interface UseConnectorMessagesReturn {
  messages: ConnectorMessage[];
  loading: boolean;
  error: string | null;
  fetchMessages: (connector?: ConnectorType) => Promise<void>;
  sendMessage: (message: Omit<ConnectorMessage, "id" | "timestamp">) => Promise<ConnectorMessage | null>;
  getTheme: (connector: ConnectorType) => ConnectorTheme;
  getLabel: (connector: ConnectorType) => string;
  connected: boolean;
}

export function useConnectorMessages(): UseConnectorMessagesReturn {
  const [messages, setMessages] = useState<ConnectorMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  // Fetch messages
  const fetchMessages = useCallback(async (connector?: ConnectorType) => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (connector) params.set("connector", connector);
      params.set("limit", "50");

      const res = await fetch(`${API_BASE}/api/connectors/messages?${params}`);
      if (!res.ok) throw new Error(`Failed to fetch messages: ${res.status}`);
      const data = await res.json();
      setMessages(data.messages ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch messages");
    } finally {
      setLoading(false);
    }
  }, []);

  // Send message
  const sendMessage = useCallback(
    async (msg: Omit<ConnectorMessage, "id" | "timestamp">): Promise<ConnectorMessage | null> => {
      try {
        const res = await fetch(`${API_BASE}/api/connectors/messages`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(msg),
        });
        if (!res.ok) throw new Error(`Failed to send message: ${res.status}`);
        const data = await res.json();
        setMessages((prev) => [data, ...prev]);
        return data;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to send message");
        return null;
      }
    },
    []
  );

  // WebSocket connection for real-time messages
  useEffect(() => {
    const connectWs = () => {
      try {
        const ws = new WebSocket(`${WS_BASE}/api/connectors/ws`);
        wsRef.current = ws;

        ws.onopen = () => setConnected(true);
        ws.onclose = () => {
          setConnected(false);
          // Reconnect after 5 seconds
          setTimeout(connectWs, 5000);
        };
        ws.onerror = () => setConnected(false);

        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === "connector_message" && msg.data) {
              setMessages((prev) => [msg.data, ...prev]);
            }
          } catch {
            // Ignore non-JSON messages
          }
        };
      } catch {
        // WebSocket not available
      }
    };

    connectWs();

    return () => {
      wsRef.current?.close();
    };
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchMessages();
  }, [fetchMessages]);

  const getTheme = useCallback((connector: ConnectorType) => {
    return CONNECTOR_THEMES[connector] || CONNECTOR_THEMES.system;
  }, []);

  const getLabel = useCallback((connector: ConnectorType) => {
    return CONNECTOR_LABELS[connector] || connector;
  }, []);

  return {
    messages,
    loading,
    error,
    fetchMessages,
    sendMessage,
    getTheme,
    getLabel,
    connected,
  };
}

// Export helpers for use in components without hook
export function getConnectorTheme(connector: ConnectorType): ConnectorTheme {
  return CONNECTOR_THEMES[connector] || CONNECTOR_THEMES.system;
}

export function getConnectorLabel(connector: ConnectorType): string {
  return CONNECTOR_LABELS[connector] || connector;
}
