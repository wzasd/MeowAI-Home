/** TTS (Text-to-Speech) button using backend Edge TTS */

import { useState, useCallback, useRef } from "react";
import { Volume2, VolumeX, Loader2 } from "lucide-react";
import { api } from "../../api/client";
import { useThreadStore } from "../../stores/threadStore";

interface TTSButtonProps {
  content: string;
  catId: string;
  catName?: string;
}

type TTSState = "idle" | "loading" | "playing";

export function TTSButton({ content, catId, catName = "猫咪" }: TTSButtonProps) {
  const [state, setState] = useState<TTSState>("idle");
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const currentThreadId = useThreadStore((s) => s.currentThreadId);

  const stopSpeaking = useCallback(() => {
    audioRef.current?.pause();
    audioRef.current = null;
    setState("idle");
  }, []);

  const startSpeaking = useCallback(async () => {
    if (!currentThreadId) {
      console.warn("No active thread for TTS");
      return;
    }

    stopSpeaking();
    setState("loading");

    try {
      const blob = await api.voice.tts(content, catId, currentThreadId);
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audioRef.current = audio;

      audio.onplay = () => setState("playing");
      audio.onended = () => {
        setState("idle");
        URL.revokeObjectURL(url);
      };
      audio.onerror = () => {
        setState("idle");
        URL.revokeObjectURL(url);
      };

      await audio.play();
    } catch (e) {
      console.error("TTS failed:", e);
      setState("idle");
    }
  }, [content, catId, currentThreadId, stopSpeaking]);

  const handleClick = () => {
    if (state === "playing") {
      stopSpeaking();
    } else {
      startSpeaking();
    }
  };

  const icons: Record<TTSState, React.ReactNode> = {
    idle: <Volume2 size={14} />,
    loading: <Loader2 size={14} className="animate-spin" />,
    playing: <VolumeX size={14} />,
  };

  const titles: Record<TTSState, string> = {
    idle: `播放${catName}的语音`,
    loading: "加载中...",
    playing: "停止播放",
  };

  return (
    <button
      onClick={handleClick}
      className={`flex h-6 w-6 items-center justify-center rounded-full transition-colors ${
        state === "playing"
          ? "bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"
          : "text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300"
      }`}
      title={titles[state]}
      disabled={state === "loading"}
    >
      {icons[state]}
    </button>
  );
}
