import { useRef, useState } from "react";
import { Paperclip, Loader2, X } from "lucide-react";
import { api } from "../../api/client";
import type { Attachment } from "../../types";

interface FileUploadProps {
  threadId: string | null;
  disabled?: boolean;
  onUpload: (attachment: Attachment) => void;
}

export function FileUpload({ threadId, disabled, onUpload }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  const handleClick = () => {
    inputRef.current?.click();
  };

  const handleChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || !threadId) return;

    setUploading(true);
    for (const file of Array.from(files)) {
      try {
        const attachment = await api.uploads.upload(threadId, file);
        onUpload(attachment);
      } catch (err) {
        console.error("Upload failed:", err);
        alert(`上传失败: ${file.name}`);
      }
    }
    setUploading(false);
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  };

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        multiple
        className="hidden"
        onChange={handleChange}
        disabled={disabled || uploading}
      />
      <button
        type="button"
        onClick={handleClick}
        disabled={disabled || uploading || !threadId}
        className="rounded-xl p-2.5 text-gray-500 transition-colors hover:bg-gray-100 hover:text-gray-700 disabled:cursor-not-allowed disabled:opacity-40"
        title="上传附件"
      >
        {uploading ? <Loader2 size={18} className="animate-spin" /> : <Paperclip size={18} />}
      </button>
    </>
  );
}

interface AttachmentChipProps {
  attachment: Attachment;
  onRemove: () => void;
}

export function AttachmentChip({ attachment, onRemove }: AttachmentChipProps) {
  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="flex items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-700">
      <span className="max-w-[120px] truncate text-gray-700 dark:text-gray-200">{attachment.name}</span>
      <span className="text-xs text-gray-400">{formatSize(attachment.size)}</span>
      <button
        onClick={onRemove}
        className="rounded p-0.5 text-gray-400 hover:bg-gray-200 hover:text-gray-600 dark:hover:bg-gray-600"
      >
        <X size={12} />
      </button>
    </div>
  );
}
