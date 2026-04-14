/** WebSocket manager for MeowAI Home streaming. */

type WSMessage = { type: string; [key: string]: unknown };
type Handler = (data: WSMessage) => void;

export class WSManager {
  private ws: WebSocket | null = null;
  private handlers: Map<string, Handler[]> = new Map();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private retries = 0;
  private maxRetries = 10;

  connect(threadId: string) {
    const baseUrl = import.meta.env.VITE_WS_URL || `ws://localhost:8000`;
    const url = `${baseUrl}/ws/${threadId}`;

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log("[WS] Connected to", url);
      this.retries = 0;
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const type = data.type;
        const handlers = this.handlers.get(type) || [];
        handlers.forEach((h) => h(data));
        // Also call wildcard handlers
        const wildcards = this.handlers.get("*") || [];
        wildcards.forEach((h) => h(data));
      } catch {
        // Ignore malformed messages
      }
    };

    this.ws.onclose = () => {
      if (this.retries < this.maxRetries) {
        const delay = Math.min(1000 * Math.pow(2, this.retries), 30000);
        this.reconnectTimer = setTimeout(() => {
          this.retries++;
          this.connect(threadId);
        }, delay);
      }
    };

    this.ws.onerror = () => {
      // onclose will fire after this
    };
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    if (this.ws) {
      this.ws.onclose = null; // Prevent reconnect
      this.ws.close();
      this.ws = null;
    }
    this.handlers.clear();
  }

  send(content: string) {
    console.log("[WS] send() called, readyState=", this.ws?.readyState);
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: "send_message", content }));
    }
  }

  on(type: string, handler: Handler) {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, []);
    }
    this.handlers.get(type)!.push(handler);
  }

  off(type: string, handler: Handler) {
    const handlers = this.handlers.get(type);
    if (handlers) {
      const idx = handlers.indexOf(handler);
      if (idx >= 0) handlers.splice(idx, 1);
    }
  }

  get isConnected() {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
