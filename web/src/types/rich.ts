/** Rich content block types for agent responses. */

export type RichBlockType = "card" | "diff" | "checklist" | "file" | "media" | "interactive" | "audio";

export interface CardField {
  label: string;
  value: string;
}

export interface CardAction {
  label: string;
  action: string;
  primary?: boolean;
}

export interface CardBlock {
  type: "card";
  title?: string;
  variant: "info" | "success" | "warning" | "danger";
  fields?: CardField[];
  actions?: CardAction[];
  footer?: string;
}

export interface DiffHunk {
  oldPath?: string;
  newPath?: string;
  content: string;
}

export interface DiffBlock {
  type: "diff";
  hunks: DiffHunk[];
  summary?: string;
}

export interface ChecklistItem {
  id: string;
  text: string;
  checked: boolean;
}

export interface ChecklistBlock {
  type: "checklist";
  title?: string;
  items: ChecklistItem[];
}

export interface FileBlock {
  type: "file";
  name: string;
  mimeType?: string;
  size?: number;
  url?: string;
}

export interface MediaItem {
  url: string;
  alt?: string;
  thumbnailUrl?: string;
}

export interface MediaBlock {
  type: "media";
  items: MediaItem[];
  layout?: "grid" | "carousel";
}

export interface InteractiveOption {
  label: string;
  value: string;
  description?: string;
}

export interface InteractiveBlock {
  type: "interactive";
  style: "select" | "multi_select" | "confirm" | "button_group";
  prompt: string;
  options: InteractiveOption[];
  blockId?: string;
}

export interface AudioBlock {
  type: "audio";
  url: string;
  title?: string;
  duration?: number;
  streaming?: boolean;
}

export type RichBlock = CardBlock | DiffBlock | ChecklistBlock | FileBlock | MediaBlock | InteractiveBlock | AudioBlock;

/** Parse rich blocks from message metadata. */
export function parseRichBlocks(metadata?: Record<string, unknown>): RichBlock[] {
  if (!metadata?.richBlocks || !Array.isArray(metadata.richBlocks)) return [];
  return metadata.richBlocks as RichBlock[];
}
