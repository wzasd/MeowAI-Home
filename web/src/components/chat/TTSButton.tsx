/** TTS (Text-to-Speech) button for reading messages aloud */

import { useState, useCallback } from "react";
import { Volume2, VolumeX, Loader2 } from "lucide-react";

interface TTSButtonProps {
  content: string;
  catName?: string;
}

type TTSState = "idle" | "loading" | "playing";

export function TTSButton({ content, catName = "猫咪" }: TTSButtonProps) {
  const [state, setState] = useState<TTSState>("idle");
  const [, setUtterance] = useState<SpeechSynthesisUtterance | null>(null);

  const stopSpeaking = useCallback(() => {
    window.speechSynthesis.cancel();
    setState("idle");
    setUtterance(null);
  }, []);

  const startSpeaking = useCallback(() => {
    if (!window.speechSynthesis) {
      console.warn("Browser does not support speech synthesis");
      return;
    }

    // Cancel any ongoing speech
    window.speechSynthesis.cancel();

    setState("loading");

    const u = new SpeechSynthesisUtterance(content);
    u.lang = "zh-CN";
    u.rate = 1;
    u.pitch = 1;

    u.onstart = () => {
      setState("playing");
    };

    u.onend = () => {
      setState("idle");
      setUtterance(null);
    };

    u.onerror = () => {
      setState("idle");
      setUtterance(null);
    };

    setUtterance(u);
    window.speechSynthesis.speak(u);
  }, [content]);

  const handleClick = () => {
    if (state === "playing") {
      stopSpeaking();
    } else {
      startSpeaking();
    }
  };

  // Cleanup on unmount
  // useEffect(() => {
  //   return () => {
  //     if (utterance) {
  //       window.speechSynthesis.cancel();
  //     }
  //   };
  // }, [utterance]);

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
