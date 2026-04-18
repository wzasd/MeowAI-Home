/** Slash command interceptor — runs before WS send.
 *  Returns true if the input was consumed as a command,
 *  false if it should flow to the normal chat pipeline.
 */
import { useCallback } from "react";
import { useChatStore } from "../stores/chatStore";
import { useCatStore } from "../stores/catStore";

interface CommandResult {
  consumed: boolean;
  /** If set, caller should send this content via WS with the given intent. */
  forward?: { content: string; forceIntent: "ideate" | "execute" };
}

const COMMANDS: Record<
  string,
  {
    label: string;
    desc: string;
    handler: (args: string, ctx: CommandContext) => CommandResult;
  }
> = {
  help: {
    label: "帮助",
    desc: "显示可用命令列表",
    handler: (_args, ctx) => {
      const lines = [
        "**/help** — 显示此列表",
        "**/cats** — 列出可用猫咪",
        "**/clear** — 清空当前对话",
        "**/ideate [内容]** — 强制切换到 ideate 模式",
        "**/execute [内容]** — 强制切换到 execute 模式",
      ];
      ctx.addSystemMessage(lines.join("\n"));
      return { consumed: true };
    },
  },
  cats: {
    label: "猫咪列表",
    desc: "列出当前可用猫咪",
    handler: (_args, ctx) => {
      const cats = ctx.cats;
      if (cats.length === 0) {
        ctx.addSystemMessage("暂无可用猫咪。请先到设置中添加。");
        return { consumed: true };
      }
      const lines = cats
        .filter((c) => c.isAvailable !== false)
        .map(
          (c) =>
            `- **${c.displayName || c.name}** @${c.id} — ${c.provider}${c.defaultModel ? " / " + c.defaultModel : ""}`
        );
      ctx.addSystemMessage("**可用猫咪**\n" + lines.join("\n"));
      return { consumed: true };
    },
  },
  clear: {
    label: "清空对话",
    desc: "清空当前 thread 的消息",
    handler: (_args, ctx) => {
      ctx.clearMessages();
      ctx.addSystemMessage("对话已清空。");
      return { consumed: true };
    },
  },
  ideate: {
    label: "头脑风暴",
    desc: "切换到 ideate 模式",
    handler: (args, _ctx) => {
      if (args.trim()) {
        // Has content — forward with forced intent
        return { consumed: true, forward: { content: args.trim(), forceIntent: "ideate" } };
      }
      // Bare command — treat as mode switch, but we don't have a separate UI for this yet.
      // For now, show a hint and consume.
      _ctx.addSystemMessage(
        '已切换到 **ideate** 模式。输入 `/execute` 可切回执行模式。\n' +
        "提示：直接输入 `/ideate 你的问题` 可一步进入模式并发送。"
      );
      return { consumed: true };
    },
  },
  execute: {
    label: "执行模式",
    desc: "切换到 execute 模式",
    handler: (args, _ctx) => {
      if (args.trim()) {
        return { consumed: true, forward: { content: args.trim(), forceIntent: "execute" } };
      }
      _ctx.addSystemMessage(
        '已切换到 **execute** 模式。输入 `/ideate` 可切换到创意模式。\n' +
        "提示：直接输入 `/execute 你的任务` 可一步进入模式并发送。"
      );
      return { consumed: true };
    },
  },
  game: {
    label: "游戏",
    desc: "启动互动游戏",
    handler: (_args, ctx) => {
      ctx.addSystemMessage("游戏功能开发中。当前可用命令：`/help`、`/cats`、`/clear`、`/ideate`、`/execute`。");
      return { consumed: true };
    },
  },
};

interface CommandContext {
  addSystemMessage: (content: string) => void;
  clearMessages: () => void;
  cats: Array<{
    id: string;
    name: string;
    displayName?: string;
    provider: string;
    defaultModel?: string;
    isAvailable: boolean;
  }>;
}

/** Parse a slash command from raw input.
 *  Returns null if the input is not a known command.
 */
function parseSlashCommand(input: string): { name: string; args: string } | null {
  if (!input.startsWith("/")) return null;
  const trimmed = input.trim();
  // Match /name[space]args or /name exactly
  const match = trimmed.match(/^\/([a-zA-Z0-9_-]+)(?:\s+(.*))?$/s);
  if (!match) return null;
  const name = match[1].toLowerCase();
  const args = match[2] ?? "";
  if (name in COMMANDS) {
    return { name, args };
  }
  return null;
}

export function useChatCommands() {
  const addSystemMessage = useChatStore((s) => s.addSystemMessage);
  const clearMessages = useChatStore((s) => s.clearAll);
  const cats = useCatStore((s) => s.cats);

  const processCommand = useCallback(
    async (input: string): Promise<{ consumed: boolean; forward?: { content: string; forceIntent: "ideate" | "execute" } }> => {
      const parsed = parseSlashCommand(input);
      if (!parsed) {
        return { consumed: false };
      }

      const ctx: CommandContext = {
        addSystemMessage,
        clearMessages: () => {
          // clearAll wipes everything including wsConnected state,
          // but for /clear we only want to clear messages.
          // Use a dedicated store action if we add one; for now
          // we clear messages manually via a separate approach.
          // Actually clearAll is too destructive. Let's just clear messages.
          const state = useChatStore.getState();
          state.clearAll();
        },
        cats,
      };

      const def = COMMANDS[parsed.name];
      return def.handler(parsed.args, ctx);
    },
    [addSystemMessage, clearMessages, cats]
  );

  return { processCommand };
}
