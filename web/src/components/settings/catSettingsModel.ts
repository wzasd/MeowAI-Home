import type { Cat } from "../../stores/catStore";
import type { SettingsSummaryCardModel } from "./settingsSummaryModels";

export interface CatMutationDraft {
  displayName: string;
  provider: string;
  defaultModel: string;
  personality: string;
  mentionPatterns: string;
}

export interface CatMutationPayload {
  name: string;
  displayName: string;
  provider: string;
  defaultModel?: string;
  personality?: string;
  mentionPatterns: string[];
}

export interface CatSettingsEntryModel {
  id: string;
  title: string;
  metaLabel: string;
  providerLabel: string;
  providerKey: string;
  defaultModelLabel: string;
  mentionPatterns: string[];
  mentionCountLabel: string;
  mentionSummary: string;
  personalityPreview?: string;
  roleLabels: string[];
  roleSummary?: string;
  availabilityLabel: string;
  isAvailable: boolean;
  isDefault: boolean;
  needsAttention: boolean;
  attentionReasons: string[];
  attentionSummary?: string;
}

export interface CatSettingsModel {
  summaryCards: SettingsSummaryCardModel[];
  entries: CatSettingsEntryModel[];
}

const PROVIDER_LABELS: Record<string, string> = {
  anthropic: "Anthropic",
  openai: "OpenAI",
  google: "Google",
  dare: "Dare",
  opencode: "OpenCode",
};

function trimText(value: string): string {
  return value.trim();
}

function trimList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeTextList(values?: string[]): string[] {
  return (values ?? []).map((item) => trimText(item)).filter(Boolean);
}

function summarizeInline(values: string[], emptyLabel: string, separator: string): string {
  return values.length > 0 ? values.join(separator) : emptyLabel;
}

function getMentionCountLabel(mentionPatterns: string[]): string {
  return mentionPatterns.length > 0 ? `${mentionPatterns.length} 个提及入口` : "未配置提及入口";
}

function getCatTitle(cat: Cat): string {
  return trimText(cat.displayName || cat.name || cat.id);
}

function getProviderLabel(provider: string): string {
  return PROVIDER_LABELS[provider] ?? provider;
}

function getAttentionReasons(cat: Cat): string[] {
  const reasons: string[] = [];
  const mentionPatterns = normalizeTextList(cat.mentionPatterns);

  if (!trimText(cat.defaultModel || "")) {
    reasons.push("未配置默认模型");
  }

  if (mentionPatterns.length === 0) {
    reasons.push("未配置 @ 提及别名");
  }

  return reasons;
}

export function buildCatMutationPayload(draft: CatMutationDraft): CatMutationPayload {
  const displayName = trimText(draft.displayName);
  const defaultModel = trimText(draft.defaultModel);
  const personality = trimText(draft.personality);

  return {
    name: displayName,
    displayName,
    provider: draft.provider,
    defaultModel: defaultModel || undefined,
    personality: personality || undefined,
    mentionPatterns: trimList(draft.mentionPatterns),
  };
}

function buildSummaryCards(cats: Cat[], defaultCatId: string | null): SettingsSummaryCardModel[] {
  const availableCount = cats.filter((cat) => cat.isAvailable).length;
  const reviewCount = cats.filter((cat) => getAttentionReasons(cat).length > 0).length;
  const defaultCat = cats.find((cat) => cat.id === defaultCatId);
  const providerCount = new Set(cats.map((cat) => cat.provider).filter(Boolean)).size;
  const missingModelCount = cats.filter((cat) => !trimText(cat.defaultModel || "")).length;
  const missingMentionCount = cats.filter((cat) => normalizeTextList(cat.mentionPatterns).length === 0)
    .length;

  return [
    {
      id: "configured-cats",
      label: "已配置猫咪",
      value: String(cats.length),
      detail: `${providerCount} 个 Provider · ${Math.max(cats.length - availableCount, 0)} 只暂不可用`,
      tone: cats.length > 0 ? "neutral" : "attention",
    },
    {
      id: "availability",
      label: "在线状态",
      value: cats.length > 0 ? `${availableCount}/${cats.length}` : "0",
      detail:
        availableCount === cats.length && cats.length > 0
          ? "当前都可直接唤起"
          : "有猫咪尚未接通或当前不可用",
      tone: availableCount === cats.length && cats.length > 0 ? "success" : "attention",
    },
    {
      id: "default-cat",
      label: "默认身份",
      value: defaultCat ? getCatTitle(defaultCat) : "未设置",
      detail: defaultCat
        ? `${getProviderLabel(defaultCat.provider)} · ${trimText(defaultCat.defaultModel || "") || "未配置默认模型"}`
        : "当前没有默认入口",
      tone: defaultCat ? "accent" : "attention",
    },
    {
      id: "review",
      label: "待补资料",
      value: String(reviewCount),
      detail: `${missingModelCount} 只缺模型 · ${missingMentionCount} 只缺 @ 别名`,
      tone: reviewCount > 0 ? "attention" : "success",
    },
  ];
}

export function buildCatSettingsModel({
  cats,
  defaultCatId,
}: {
  cats: Cat[];
  defaultCatId: string | null;
}): CatSettingsModel {
  const entries = [...cats]
    .map((cat) => {
      const attentionReasons = getAttentionReasons(cat);
      const mentionPatterns = normalizeTextList(cat.mentionPatterns);
      const roleLabels = normalizeTextList(cat.roles);
      return {
        id: cat.id,
        title: getCatTitle(cat),
        metaLabel: `${cat.id} · ${getProviderLabel(cat.provider)}`,
        providerLabel: getProviderLabel(cat.provider),
        providerKey: cat.provider,
        defaultModelLabel: trimText(cat.defaultModel || "") || "未配置默认模型",
        mentionPatterns,
        mentionCountLabel: getMentionCountLabel(mentionPatterns),
        mentionSummary: summarizeInline(mentionPatterns, "暂未配置", " · "),
        personalityPreview: trimText(cat.personality || "") || undefined,
        roleLabels,
        roleSummary:
          roleLabels.length > 0 ? summarizeInline(roleLabels, "", " / ") : undefined,
        availabilityLabel: cat.isAvailable ? "当前可用" : "暂不可用",
        isAvailable: cat.isAvailable,
        isDefault: cat.id === defaultCatId,
        needsAttention: attentionReasons.length > 0,
        attentionReasons,
        attentionSummary:
          attentionReasons.length > 0 ? `待补资料：${attentionReasons.join("，")}` : undefined,
      } satisfies CatSettingsEntryModel;
    })
    .sort((left, right) => {
      if (left.isDefault !== right.isDefault) {
        return left.isDefault ? -1 : 1;
      }
      if (left.isAvailable !== right.isAvailable) {
        return left.isAvailable ? -1 : 1;
      }
      if (left.needsAttention !== right.needsAttention) {
        return left.needsAttention ? 1 : -1;
      }
      return left.title.localeCompare(right.title, "zh-Hans-CN");
    });

  return {
    summaryCards: buildSummaryCards(cats, defaultCatId),
    entries,
  };
}
