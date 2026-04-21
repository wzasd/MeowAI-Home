/** WebSocket manager for MeowAI Home streaming. */

import type { Attachment } from "../types";
import { buildWsUrl } from "./runtimeConfig";

type WSMessage = { type: string; [key: string]: unknown };
type Handler = (data: WSMessage) => void;

export class WSManager {
  private ws: WebSocket | null = null;
  private handlers: Map<string, Handler[]> = new Map();
  private connectionHandlers: ((connected: boolean) => void)[] = [];
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private retries = 0;
  private maxRetries = 10;

  onConnectionChange(handler: (connected: boolean) => void) {
    this.connectionHandlers.push(handler);
  }

  private notifyConnection(connected: boolean) {
    this.connectionHandlers.forEach((h) => h(connected));
  }

  connect(threadId: string) {
    const url = buildWsUrl(`/ws/${threadId}`);

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log("[WS] Connected to", url);
      this.retries = 0;
      this.notifyConnection(true);
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
      this.notifyConnection(false);
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

  send(content: string, attachments?: Attachment[]) {
    console.log("[WS] send() called, readyState=", this.ws?.readyState);
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: "send_message", content, attachments }));
    }
  }

  sendCommand(content: string, forceIntent: "ideate" | "execute", attachments?: Attachment[]) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({ type: "send_message", content, attachments, forceIntent })
      );
    }
  }

  sendWithDeliveryMode(
    content: string,
    deliveryMode: "queue" | "force",
    attachments?: Attachment[]
  ) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(
        JSON.stringify({ type: "send_message", content, attachments, deliveryMode })
      );
    }
  }

  cancelQueueEntry(entryId: string) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: "cancel_queue_entry", entry_id: entryId }));
    }
  }

  sendInteractiveAction(blockId: string, values: string[]) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: "interactive_action", block_id: blockId, values }));
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
