/** React hook for WebSocket connection to a thread. */

import { useEffect, useRef } from "react";
import { WSManager } from "../api/websocket";
import { useThreadStore } from "../stores/threadStore";
import { useChatStore } from "../stores/chatStore";
import type { MessageResponse } from "../types";

export function useWebSocket() {
  const currentThreadId = useThreadStore((s) => s.currentThreadId);
  const wsRef = useRef<WSManager | null>(null);

  const addLocalMessage = useChatStore((s) => s.addLocalMessage);
  const addStreamingResponse = useChatStore((s) => s.addStreamingResponse);
  const addStreamingThinking = useChatStore((s) => s.addStreamingThinking);
  const stopStreaming = useChatStore((s) => s.stopStreaming);
  const fetchMessages = useChatStore((s) => s.fetchMessages);
  const setSkill = useChatStore((s) => s.setSkill);
  const setIntentMode = useChatStore((s) => s.setIntentMode);

  useEffect(() => {
    if (!currentThreadId) return;

    const ws = new WSManager();
    wsRef.current = ws;

    // Listen for WS events
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

    ws.on("error", (data) => {
      console.error("WebSocket error:", data.message);
      stopStreaming();
    });

    ws.connect(currentThreadId);

    // Listen for send events from InputBar
    const handleSend = (e: Event) => {
      const { content } = (e as CustomEvent).detail;
      if (content) {
        ws.send(content);
      }
    };
    window.addEventListener("meowai:send", handleSend);

    return () => {
      ws.disconnect();
      wsRef.current = null;
      window.removeEventListener("meowai:send", handleSend);
    };
  }, [currentThreadId]);

  return wsRef;
}
