/** React hook for WebSocket connection to a thread. */

import { useEffect, useRef } from "react";
import { WSManager } from "../api/websocket";
import { useThreadStore } from "../stores/threadStore";
import { useChatStore } from "../stores/chatStore";
import type { MessageResponse, Attachment } from "../types";

export function useWebSocket() {
  const currentThreadId = useThreadStore((s) => s.currentThreadId);
  const wsRef = useRef<WSManager | null>(null);
  const connectedIdRef = useRef<string | null>(null);
  const mountedRef = useRef(false);

  const addLocalMessage = useChatStore((s) => s.addLocalMessage);
  const addStreamingResponse = useChatStore((s) => s.addStreamingResponse);
  const addStreamingThinking = useChatStore((s) => s.addStreamingThinking);
  const stopStreaming = useChatStore((s) => s.stopStreaming);
  const fetchMessages = useChatStore((s) => s.fetchMessages);
  const setSkill = useChatStore((s) => s.setSkill);
  const setIntentMode = useChatStore((s) => s.setIntentMode);

  // Track first mount (skip Strict Mode double-fire)
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  useEffect(() => {
    if (!currentThreadId) return;

    // Skip reconnect if already connected to this exact thread
    if (connectedIdRef.current === currentThreadId && wsRef.current?.isConnected) {
      return;
    }

    // Disconnect previous
    if (wsRef.current) {
      wsRef.current.disconnect();
      wsRef.current = null;
      connectedIdRef.current = null;
    }

    const ws = new WSManager();
    wsRef.current = ws;
    connectedIdRef.current = currentThreadId;

    ws.on("message_sent", (data) => {
      addLocalMessage(data.message as MessageResponse);
    });
    ws.on("intent_mode", (data) => {
      setIntentMode(data.mode as string);
    });
    ws.on("cat_response", (data) => {
      addStreamingResponse(data.cat_id as string, {
        catId: data.cat_id as string,
        catName: data.cat_name as string,
        content: data.content as string,
        targetCats: data.target_cats as string[] | null,
      });
    });
    ws.on("skill_activated", (data) => {
      setSkill(data.skill_name as string);
    });
    ws.on("thinking", (data) => {
      addStreamingThinking(data.cat_id as string, data.content as string);
    });
    ws.on("done", () => {
      stopStreaming();
      fetchMessages(currentThreadId);
    });
    ws.on("session_created", () => {
      window.dispatchEvent(new CustomEvent("meowai:session_created"));
    });
    ws.on("error", (data) => {
      console.error("WebSocket error:", data.message);
      stopStreaming();
    });

    ws.connect(currentThreadId);

    // DO NOT disconnect on cleanup — prevents React Strict Mode from killing the connection.
    // The next effect run for a different threadId will disconnect this one above.
  }, [currentThreadId]);

  // Stable send handler — always uses wsRef
  useEffect(() => {
    const handleSend = (e: Event) => {
      const { content, attachments } = (e as CustomEvent<{ content: string; attachments?: Attachment[] }>).detail;
      if (!content) return;
      const ws = wsRef.current;
      if (ws && ws.isConnected) {
        console.log("[WS] Sending:", content.substring(0, 60));
        ws.send(content, attachments);
      } else {
        console.error("[WS] Cannot send - ws=", !!ws, "connected=", ws?.isConnected);
      }
    };
    const handleInteractiveAction = (e: Event) => {
      const { blockId, values } = (e as CustomEvent<{ blockId: string; values: string[] }>).detail;
      const ws = wsRef.current;
      if (ws && ws.isConnected) {
        ws.sendInteractiveAction(blockId, values);
      }
    };
    window.addEventListener("meowai:send", handleSend);
    window.addEventListener("meowai:interactive_action", handleInteractiveAction);
    return () => {
      window.removeEventListener("meowai:send", handleSend);
      window.removeEventListener("meowai:interactive_action", handleInteractiveAction);
    };
  }, []);

  return wsRef;
}
