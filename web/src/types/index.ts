/** Shared TypeScript types for the MeowAI Home frontend. */

export interface ThreadResponse {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  current_cat_id: string;
  is_archived: boolean;
  message_count: number;
}

export interface ThreadDetailResponse {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  current_cat_id: string;
  is_archived: boolean;
  messages: MessageResponse[];
}

export interface MessageResponse {
  role: "user" | "assistant";
  content: string;
  cat_id: string | null;
  timestamp: string;
  thinking?: string;
  is_internal?: boolean;
  parent_id?: string;
}

export interface ThreadListResponse {
  threads: ThreadResponse[];
}

export interface MessageListResponse {
  messages: MessageResponse[];
  has_more: boolean;
}

export interface StreamingCatResponse {
  catId: string;
  catName: string;
  content: string;
  targetCats: string[] | null;
}

export const CAT_INFO: Record<string, { name: string; emoji: string; color: string }> = {
  orange: { name: "阿橘", emoji: "🐱", color: "orange" },
  inky: { name: "墨点", emoji: "🐾", color: "purple" },
  patch: { name: "花花", emoji: "🌸", color: "pink" },
};

/** Format timestamp to readable time */
export function formatTime(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}

/** Format timestamp to full datetime */
export function formatDateTime(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleString("zh-CN", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
