/** ConnectorBubble — external connector message bubble (feishu, weixin, github, etc.) */

import {
  getConnectorTheme,
  getConnectorLabel,
  type ConnectorMessage,
  type ConnectorType,
} from "../../hooks/useConnectorMessages";

function formatTime(ts: number): string {
  const d = new Date(ts);
  return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
}

function ConnectorIcon({ connector }: { connector: ConnectorType }) {
  const iconMap: Record<ConnectorType, string> = {
    feishu: "📱",
    dingtalk: "💼",
    weixin: "💬",
    wecom: "🏢",
    github: "🐙",
    scheduler: "⏰",
    system: "⚙️",
  };
  return <span className="text-sm">{iconMap[connector] || "🔗"}</span>;
}

function renderContentBlocks(blocks: ConnectorMessage["content_blocks"]) {
  if (!blocks || blocks.length === 0) return null;

  return blocks.map((block, i) => {
    if (block.type === "text" && block.text) {
      return (
        <p key={i} className="text-sm leading-relaxed text-gray-700 dark:text-gray-300">
          {block.text}
        </p>
      );
    }
    if (block.type === "image" && block.url) {
      const isSafeUrl = block.url.startsWith("/") || block.url.startsWith("http");
      return (
        <img
          key={i}
          src={block.url}
          alt="attached image"
          className="mt-2 max-w-full rounded-lg border border-gray-200 sm:max-w-sm dark:border-gray-600"
          onClick={() => isSafeUrl && window.open(block.url, "_blank", "noopener")}
        />
      );
    }
    if (block.type === "file" && block.url) {
      return (
        <a
          key={i}
          href={block.url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-2 inline-flex items-center gap-1 rounded bg-gray-100 px-3 py-1.5 text-xs text-blue-600 hover:underline dark:bg-gray-700 dark:text-blue-400"
        >
          📎 {block.text || "文件"}
        </a>
      );
    }
    return null;
  });
}

interface ConnectorBubbleProps {
  message: ConnectorMessage;
}

export function ConnectorBubble({ message }: ConnectorBubbleProps) {
  const theme = getConnectorTheme(message.connector);
  const label = getConnectorLabel(message.connector);
  const hasBlocks = message.content_blocks && message.content_blocks.length > 0;

  // Protocol whitelist — only render safe URLs as clickable links
  const srcUrl =
    message.source_url && /^https?:\/\//.test(message.source_url) ? message.source_url : undefined;

  return (
    <div className="mb-4 flex items-start gap-2">
      {/* Connector icon avatar */}
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-base ${theme.avatar}`}
      >
        <ConnectorIcon connector={message.connector} />
      </div>

      <div className="min-w-0 max-w-[85%] md:max-w-[75%]">
        {/* Header line */}
        <div className="mb-1 flex items-center gap-2">
          {srcUrl ? (
            <a
              href={srcUrl}
              target="_blank"
              rel="noopener noreferrer"
              className={`text-xs font-semibold hover:underline ${theme.label}`}
            >
              {label}
            </a>
          ) : (
            <span className={`text-xs font-semibold ${theme.label}`}>{label}</span>
          )}
          {message.sender.name && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {message.sender.name} 说
            </span>
          )}
          <span className="text-xs text-gray-400">{formatTime(message.timestamp)}</span>
        </div>

        {/* Bubble */}
        <div
          className={`overflow-hidden rounded-2xl rounded-bl-sm px-4 py-3 transition-transform hover:-translate-y-0.5 ${theme.bubble}`}
        >
          {hasBlocks ? (
            renderContentBlocks(message.content_blocks)
          ) : (
            <p className="text-sm leading-relaxed text-gray-700 dark:text-gray-300">
              {message.content}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
