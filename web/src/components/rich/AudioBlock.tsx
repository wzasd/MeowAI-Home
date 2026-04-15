import type { AudioBlock } from "../../types/rich";
import { Play, Pause, Volume2 } from "lucide-react";
import { useRef, useState } from "react";

export function AudioBlockView({ block }: { block: AudioBlock }) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleEnded = () => setIsPlaying(false);

  return (
    <div className="flex items-center gap-3 rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
      <button
        onClick={togglePlay}
        className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-600 text-white hover:bg-blue-700"
        aria-label={isPlaying ? "暂停" : "播放"}
      >
        {isPlaying ? <Pause size={18} /> : <Play size={18} className="ml-0.5" />}
      </button>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 text-sm font-medium text-gray-800 dark:text-gray-200">
          <Volume2 size={14} className="text-gray-400" />
          <span className="truncate">{block.title || "音频消息"}</span>
        </div>
        {block.duration !== undefined && (
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {Math.floor(block.duration / 60)}:{String(Math.floor(block.duration % 60)).padStart(2, "0")}
          </div>
        )}
      </div>
      <audio
        ref={audioRef}
        src={block.url}
        onEnded={handleEnded}
        className="hidden"
        preload="metadata"
      />
    </div>
  );
}
