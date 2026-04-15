/** Simple audio player wrapper with play/pause toggle. */

import { useRef, useState, useEffect } from "react";
import { Play, Pause, Loader2 } from "lucide-react";

interface AudioPlayerProps {
  src: string;
  size?: number;
}

type PlayerState = "idle" | "loading" | "playing";

export function AudioPlayer({ src, size = 14 }: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [state, setState] = useState<PlayerState>("idle");

  useEffect(() => {
    // Preload audio
    const audio = new Audio(src);
    audioRef.current = audio;

    audio.oncanplaythrough = () => {
      if (state === "loading") {
        audio.play().catch(() => setState("idle"));
      }
    };

    audio.onplay = () => setState("playing");
    audio.onended = () => setState("idle");
    audio.onpause = () => setState("idle");
    audio.onerror = () => setState("idle");

    return () => {
      audio.pause();
      audioRef.current = null;
    };
  }, [src]);

  const toggle = () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (state === "playing") {
      audio.pause();
      setState("idle");
    } else {
      setState("loading");
      audio.play().catch(() => setState("idle"));
    }
  };

  const icon =
    state === "playing" ? (
      <Pause size={size} />
    ) : state === "loading" ? (
      <Loader2 size={size} className="animate-spin" />
    ) : (
      <Play size={size} />
    );

  return (
    <button
      onClick={toggle}
      className="flex items-center justify-center rounded-full transition-colors"
      title={state === "playing" ? "暂停" : "播放"}
      disabled={state === "loading"}
    >
      {icon}
    </button>
  );
}
