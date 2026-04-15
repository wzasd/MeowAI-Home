/** Voice input using MediaRecorder + backend Whisper ASR */

import { useState, useRef, useCallback } from "react";
import { Mic, MicOff, Loader2 } from "lucide-react";
import { api } from "../../api/client";

interface VoiceInputProps {
  onTranscript: (text: string) => void;
  disabled?: boolean;
}

type RecordState = "idle" | "recording" | "processing";

export function VoiceInput({ onTranscript, disabled }: VoiceInputProps) {
  const [state, setState] = useState<RecordState>("idle");
  const [isSupported, setIsSupported] = useState<boolean | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const checkSupport = useCallback(() => {
    if (isSupported !== null) return isSupported;
    const supported = typeof navigator !== "undefined" && !!navigator.mediaDevices?.getUserMedia;
    setIsSupported(supported);
    return supported;
  }, [isSupported]);

  const startRecording = useCallback(async () => {
    if (!checkSupport()) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm")
        ? "audio/webm"
        : MediaRecorder.isTypeSupported("audio/mp4")
        ? "audio/mp4"
        : "";

      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);

      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      recorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: mimeType || "audio/webm" });
        chunksRef.current = [];
        setState("processing");

        try {
          const result = await api.voice.asr(blob, "zh");
          onTranscript(result.text);
        } catch (e) {
          console.error("ASR failed:", e);
        } finally {
          setState("idle");
          stream.getTracks().forEach((t) => t.stop());
        }
      };

      recorder.start();
      setState("recording");
    } catch (e) {
      console.error("Failed to start recording:", e);
      setState("idle");
    }
  }, [checkSupport, onTranscript]);

  const stopRecording = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      recorder.stop();
    }
  }, []);

  const toggleRecording = () => {
    if (state === "recording") {
      stopRecording();
    } else if (state === "idle") {
      startRecording();
    }
  };

  if (isSupported === false) {
    return null;
  }

  const icon =
    state === "recording" ? (
      <MicOff size={18} />
    ) : state === "processing" ? (
      <Loader2 size={18} className="animate-spin" />
    ) : (
      <Mic size={18} />
    );

  return (
    <button
      onClick={toggleRecording}
      disabled={disabled || state === "processing"}
      className={`rounded-xl p-2.5 transition-colors ${
        state === "recording"
          ? "animate-pulse bg-red-500 text-white hover:bg-red-600"
          : "bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300"
      } disabled:cursor-not-allowed disabled:opacity-40`}
      title={state === "recording" ? "停止录音" : state === "processing" ? "识别中..." : "语音输入"}
    >
      {icon}
    </button>
  );
}
