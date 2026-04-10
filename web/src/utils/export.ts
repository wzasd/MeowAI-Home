/** Export conversation to Markdown */

import type { ThreadResponse, MessageResponse } from "../types";
import { CAT_INFO } from "../types";

interface ExportData {
  thread: Pick<ThreadResponse, "name" | "created_at" | "current_cat_id"> & {
    message_count?: number;
  };
  messages: MessageResponse[];
}

export function exportToMarkdown(data: ExportData): string {
  const { thread, messages } = data;

  const lines: string[] = [];

  // Header
  lines.push(`# ${thread.name}`);
  lines.push("");
  lines.push(`- **创建时间**: ${new Date(thread.created_at).toLocaleString("zh-CN")}`);
  lines.push(`- **消息数量**: ${thread.message_count || messages.length}`);
  lines.push(`- **当前猫咪**: ${CAT_INFO[thread.current_cat_id]?.name || thread.current_cat_id}`);
  lines.push("");
  lines.push("---");
  lines.push("");

  // Messages
  for (const msg of messages) {
    const timestamp = new Date(msg.timestamp).toLocaleString("zh-CN");

    if (msg.role === "user") {
      lines.push(`**用户** (${timestamp}):`);
      lines.push("");
      lines.push(msg.content);
    } else {
      const catName = msg.cat_id ? CAT_INFO[msg.cat_id]?.name || msg.cat_id : "助手";
      const catEmoji = msg.cat_id ? CAT_INFO[msg.cat_id]?.emoji || "🐱" : "🤖";
      lines.push(`${catEmoji} **${catName}** (${timestamp}):`);
      lines.push("");
      lines.push(msg.content);

      if (msg.thinking) {
        lines.push("");
        lines.push("<details>");
        lines.push("<summary>思考过程</summary>");
        lines.push("");
        lines.push(msg.thinking);
        lines.push("</details>");
      }
    }

    lines.push("");
    lines.push("---");
    lines.push("");
  }

  // Footer
  lines.push("");
  lines.push("*Exported from MeowAI Home*");

  return lines.join("\n");
}

export function downloadMarkdown(filename: string, content: string): void {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename.endsWith(".md") ? filename : `${filename}.md`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export function copyToClipboard(text: string): Promise<boolean> {
  return navigator.clipboard
    .writeText(text)
    .then(() => true)
    .catch(() => false);
}
