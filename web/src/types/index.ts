/** Shared TypeScript types for the MeowAI Home frontend. */

export interface ThreadResponse {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  current_cat_id: string;
  is_archived: boolean;
  message_count: number;
  project_path?: string;
}

export interface ThreadDetailResponse {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  current_cat_id: string;
  is_archived: boolean;
  messages: MessageResponse[];
  project_path?: string;
}

export interface MessageResponse {
  role: "user" | "assistant";
  content: string;
  cat_id: string | null;
  timestamp: string;
  thinking?: string;
  is_internal?: boolean;
  parent_id?: string;
  id: string;
  metadata?: Record<string, unknown>;
  is_deleted?: boolean;
  is_edited?: boolean;
  reply_to?: string;
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

export interface CatResponse {
  id: string;
  name: string;
  displayName?: string;
  provider: string;
  avatar?: string;
  colorPrimary?: string;
  colorSecondary?: string;
  mentionPatterns?: string[];
  isAvailable: boolean;
  roles?: string[];
  evaluation?: string;
  accountRef?: string;
}

export interface CatListResponse {
  cats: CatResponse[];
  defaultCat: string | null;
}

export interface CatDetailResponse extends CatResponse {
  defaultModel?: string;
  personality?: string;
  cliCommand?: string;
  cliArgs?: string[];
}

export const CAT_INFO: Record<string, { name: string; emoji: string; color: string }> = {
  orange: { name: "阿橘", emoji: "🐱", color: "orange" },
  inky: { name: "墨点", emoji: "🐾", color: "purple" },
  patch: { name: "花花", emoji: "🌸", color: "pink" },
};

export interface ConnectorResponse {
  name: string;
  displayName: string;
  enabled: boolean;
  status: string;
  features: string[];
  configFields: string[];
}

export interface ConnectorListResponse {
  connectors: ConnectorResponse[];
}

export interface ConnectorBindingStatus {
  name: string;
  bound: boolean;
  bound_at: string | null;
  bound_user: string | null;
}

export interface ConnectorQrResponse {
  name: string;
  qr_data_url: string;
  bind_url: string;
  expires_in: number;
  token: string;
}

export interface EnvVarResponse {
  name: string;
  category: string;
  description: string;
  default: string | null;
  current: string;
  isSet: boolean;
  required: boolean;
  sensitive: boolean;
  allowedValues: string[] | null;
}

export interface EnvVarListResponse {
  variables: EnvVarResponse[];
  categories: string[];
}

export type AuthType = "subscription" | "api_key";
export type Protocol = "anthropic" | "openai" | "google" | "opencode";

export interface AccountResponse {
  id: string;
  displayName: string;
  protocol: Protocol;
  authType: AuthType;
  baseUrl: string | null;
  models: string[] | null;
  isBuiltin: boolean;
  hasApiKey: boolean;
}

export interface AccountListResponse {
  accounts: AccountResponse[];
}

export interface TestKeyResponse {
  valid: boolean;
  error?: string;
}

export interface CapabilityBoardItem {
  id: string;
  type: "mcp" | "skill";
  source: string;
  enabled: boolean;
  description?: string;
  triggers?: string[];
  cats: Record<string, boolean>;
  connectionStatus?: "connected" | "error" | "timeout" | "unsupported";
  tools?: Array<{ name: string; description?: string }>;
  probeError?: string;
}

export interface CapabilityBoardResponse {
  items: CapabilityBoardItem[];
  projectPath: string;
}

export interface CapabilityPatchRequest {
  capabilityId: string;
  capabilityType: "mcp" | "skill";
  scope: "global" | "cat";
  enabled: boolean;
  catId?: string;
  projectPath?: string;
}

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
