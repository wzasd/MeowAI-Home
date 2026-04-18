import type { Cat } from "../../stores/catStore";

export interface CatMentionOption {
  id: string;
  name: string;
  emoji: string;
  color: string;
  bgColor: string;
  aliases: string[];
  desc: string;
  toneClass: string;
  aliasClass: string;
  borderClass: string;
}

type MentionableCat = Pick<
  Cat,
  "id" | "name" | "displayName" | "provider" | "defaultModel" | "avatar" | "mentionPatterns" | "isAvailable"
>;

const STYLE_PALETTES = [
  {
    emoji: "🐱",
    color: "text-orange-700",
    bgColor: "bg-orange-100",
    toneClass:
      "bg-[linear-gradient(135deg,rgba(255,236,214,0.95),rgba(255,255,255,0.9)_45%,rgba(255,229,190,0.88))] dark:bg-[linear-gradient(135deg,rgba(230,162,93,0.16),rgba(255,255,255,0.05)_45%,rgba(201,133,67,0.14))]",
    aliasClass:
      "bg-orange-100/85 text-orange-800 ring-1 ring-orange-200/70 dark:bg-orange-400/12 dark:text-orange-200 dark:ring-orange-300/20",
    borderClass: "border-orange-200/70 dark:border-orange-300/20",
  },
  {
    emoji: "🐾",
    color: "text-sky-700",
    bgColor: "bg-sky-100",
    toneClass:
      "bg-[linear-gradient(135deg,rgba(224,244,255,0.95),rgba(255,255,255,0.9)_45%,rgba(218,237,255,0.86))] dark:bg-[linear-gradient(135deg,rgba(86,177,255,0.16),rgba(255,255,255,0.05)_45%,rgba(130,198,255,0.12))]",
    aliasClass:
      "bg-sky-100/85 text-sky-800 ring-1 ring-sky-200/70 dark:bg-sky-400/12 dark:text-sky-200 dark:ring-sky-300/20",
    borderClass: "border-sky-200/70 dark:border-sky-300/20",
  },
  {
    emoji: "🌸",
    color: "text-emerald-700",
    bgColor: "bg-emerald-100",
    toneClass:
      "bg-[linear-gradient(135deg,rgba(225,250,240,0.96),rgba(255,255,255,0.9)_45%,rgba(255,233,220,0.86))] dark:bg-[linear-gradient(135deg,rgba(84,196,150,0.16),rgba(255,255,255,0.05)_45%,rgba(230,162,93,0.1))]",
    aliasClass:
      "bg-emerald-100/85 text-emerald-800 ring-1 ring-emerald-200/70 dark:bg-emerald-400/12 dark:text-emerald-200 dark:ring-emerald-300/20",
    borderClass: "border-emerald-200/70 dark:border-emerald-300/20",
  },
  {
    emoji: "✨",
    color: "text-violet-700",
    bgColor: "bg-violet-100",
    toneClass:
      "bg-[linear-gradient(135deg,rgba(239,233,255,0.95),rgba(255,255,255,0.9)_45%,rgba(232,220,255,0.88))] dark:bg-[linear-gradient(135deg,rgba(148,110,255,0.18),rgba(255,255,255,0.05)_45%,rgba(193,170,255,0.12))]",
    aliasClass:
      "bg-violet-100/85 text-violet-800 ring-1 ring-violet-200/70 dark:bg-violet-400/12 dark:text-violet-200 dark:ring-violet-300/20",
    borderClass: "border-violet-200/70 dark:border-violet-300/20",
  },
  {
    emoji: "🧠",
    color: "text-rose-700",
    bgColor: "bg-rose-100",
    toneClass:
      "bg-[linear-gradient(135deg,rgba(255,235,239,0.95),rgba(255,255,255,0.9)_45%,rgba(255,223,232,0.88))] dark:bg-[linear-gradient(135deg,rgba(255,120,149,0.18),rgba(255,255,255,0.05)_45%,rgba(255,168,186,0.12))]",
    aliasClass:
      "bg-rose-100/85 text-rose-800 ring-1 ring-rose-200/70 dark:bg-rose-400/12 dark:text-rose-200 dark:ring-rose-300/20",
    borderClass: "border-rose-200/70 dark:border-rose-300/20",
  },
] as const;

function hashValue(value: string) {
  return value.split("").reduce((sum, char) => sum + char.charCodeAt(0), 0);
}

function normalizeAlias(value: string | undefined) {
  const trimmed = value?.trim();
  if (!trimmed) return null;
  return trimmed.startsWith("@") ? trimmed : `@${trimmed}`;
}

function pickEmoji(cat: MentionableCat, fallback: string) {
  const avatar = cat.avatar?.trim();
  if (!avatar) return fallback;
  if (avatar.includes("/") || avatar.includes("http")) return fallback;
  return avatar;
}

function buildAliases(cat: MentionableCat) {
  const candidates = [
    cat.id,
    ...(cat.mentionPatterns ?? []),
    cat.displayName,
    cat.name,
  ];
  const seen = new Set<string>();
  const aliases: string[] = [];

  for (const candidate of candidates) {
    const normalized = normalizeAlias(candidate);
    if (!normalized) continue;

    const key = normalized.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    aliases.push(normalized);
  }

  return aliases;
}

export function buildCatMentionOptions(cats: MentionableCat[]): CatMentionOption[] {
  return cats
    .filter((cat) => cat.isAvailable && cat.id !== "co-creator")
    .map((cat) => {
      const palette =
        STYLE_PALETTES[hashValue(cat.id) % STYLE_PALETTES.length] ?? STYLE_PALETTES[0];
      const aliases = buildAliases(cat);

      return {
        id: cat.id,
        name: cat.displayName || cat.name || cat.id,
        emoji: pickEmoji(cat, palette.emoji),
        color: palette.color,
        bgColor: palette.bgColor,
        aliases: aliases.length > 0 ? aliases : [`@${cat.id}`],
        desc: cat.defaultModel || cat.provider,
        toneClass: palette.toneClass,
        aliasClass: palette.aliasClass,
        borderClass: palette.borderClass,
      };
    })
    .sort((left, right) => left.name.localeCompare(right.name, "zh-Hans-CN"));
}
