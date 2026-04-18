import { useEffect, useState } from "react";
import { Bot, Loader2, Pencil, Plus, Save, Trash2, X, Lock, Unlock } from "lucide-react";

import { useCatStore, type Cat } from "../../stores/catStore";
import { useAccountStore } from "../../stores/accountStore";
import { SettingsSectionCard, SettingsSummaryGrid } from "./SettingsSectionCard";
import { buildCatMutationPayload, buildCatSettingsModel } from "./catSettingsModel";

const PROVIDER_OPTIONS = [
  { value: "anthropic", label: "Anthropic (Claude)" },
  { value: "openai", label: "OpenAI (GPT)" },
  { value: "google", label: "Google (Gemini)" },
  { value: "dare", label: "Dare (Deterministic)" },
] as const;

const PROVIDER_LABELS: Record<string, string> = {
  anthropic: "Anthropic",
  openai: "OpenAI",
  google: "Google",
  dare: "Dare",
};

interface CatEditorState {
  id: string;
  displayName: string;
  accountRef: string;
  provider: string;
  defaultModel: string;
  personality: string;
  mentionPatterns: string;
  useCustomModel: boolean;
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function createEditorState(cat?: Cat): CatEditorState {
  return {
    id: cat?.id || "",
    displayName: cat?.displayName || cat?.name || "",
    accountRef: cat?.accountRef || "",
    provider: cat?.provider || "anthropic",
    defaultModel: cat?.defaultModel || "",
    personality: cat?.personality || "",
    mentionPatterns: (cat?.mentionPatterns || []).join(", "),
    useCustomModel: false,
  };
}

function AccountBadge({ accountId }: { accountId: string }) {
  const accounts = useAccountStore((s) => s.accounts);
  const account = accounts.find((a) => a.id === accountId);
  if (!account) return null;

  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-blue-200 bg-blue-50 px-2 py-0.5 text-[11px] font-medium text-blue-700 dark:border-blue-800 dark:bg-blue-900/20 dark:text-blue-400">
      <span className="h-1.5 w-1.5 rounded-full bg-blue-400" />
      {account.displayName}
      {account.authType === "api_key" ? (
        <span className="text-blue-500/70">· Key</span>
      ) : (
        <span className="text-blue-500/70">· Sub</span>
      )}
    </span>
  );
}

function CatEditor({
  cat,
  onSave,
  onCancel,
}: {
  cat?: Cat;
  onSave: (draft: CatEditorState) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState(() => createEditorState(cat));
  const isEdit = Boolean(cat);
  const canSubmit = form.displayName.trim().length > 0 && (isEdit || form.id.trim().length > 0);

  const accounts = useAccountStore((s) => s.accounts);
  const fetchAccounts = useAccountStore((s) => s.fetchAccounts);

  useEffect(() => {
    void fetchAccounts();
  }, [fetchAccounts]);

  const boundAccount = accounts.find((a) => a.id === form.accountRef);
  const isBound = Boolean(form.accountRef && boundAccount);
  const availableModels = boundAccount?.models || [];

  const handleAccountChange = (accountId: string) => {
    setForm((current) => {
      if (!accountId) {
        return { ...current, accountRef: "", useCustomModel: false };
      }
      const acc = accounts.find((a) => a.id === accountId);
      if (!acc) return { ...current, accountRef: accountId };
      return {
        ...current,
        accountRef: accountId,
        provider: acc.protocol,
        defaultModel: acc.models?.includes(current.defaultModel)
          ? current.defaultModel
          : acc.models?.[0] || "",
        useCustomModel: false,
      };
    });
  };

  return (
    <div className="nest-panel nest-r-xl border-[rgba(47,116,103,0.16)] bg-[linear-gradient(145deg,rgba(247,243,233,0.92),rgba(255,255,255,0.78))] px-5 py-5 shadow-[0_24px_60px_-38px_rgba(15,23,42,0.4)] dark:bg-[linear-gradient(145deg,rgba(33,27,23,0.96),rgba(24,18,15,0.94))]">
      <div className="flex flex-col gap-4 border-b border-[var(--line)] pb-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 max-w-3xl">
          <div className="nest-kicker">{isEdit ? "编辑档案" : "新增猫咪"}</div>
          <h4 className="mt-2 text-lg font-semibold text-[var(--text-strong)]">
            {isEdit ? "调整猫咪身份卡" : "创建新的猫咪入口"}
          </h4>
          <p className="mt-2 text-sm leading-7 text-[var(--text-soft)]">
            运行来源决定这只猫实际调用哪个 Provider 和账号。先选账号，Provider 和模型自动跟随；不绑定时手动指定。
          </p>
        </div>
        <span className="inline-flex items-center rounded-full border border-[rgba(183,103,37,0.18)] bg-[rgba(183,103,37,0.08)] px-2.5 py-1 text-[11px] font-medium text-[var(--accent-deep)] dark:bg-[rgba(230,162,93,0.14)] dark:text-[var(--accent)]">
          手动保存
        </span>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        {!isEdit && (
          <label className="block">
            <span className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--text-faint)]">
              内部 ID
            </span>
            <input
              className="nest-field nest-r-lg mt-2 block w-full px-3 py-3 text-sm"
              value={form.id}
              onChange={(event) => setForm((current) => ({ ...current, id: event.target.value }))}
              placeholder="例如 gemini"
            />
            <p className="mt-2 text-xs leading-6 text-[var(--text-faint)]">
              ID 用来稳定引用和路由，创建后不要频繁改。
            </p>
          </label>
        )}

        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--text-faint)]">
            展示名称
          </span>
          <input
            className="nest-field nest-r-lg mt-2 block w-full px-3 py-3 text-sm"
            value={form.displayName}
            onChange={(event) =>
              setForm((current) => ({ ...current, displayName: event.target.value }))
            }
            placeholder="例如 烁烁"
          />
        </label>
      </div>

      {/* ── 运行来源 ── */}
      <div className="mt-5 rounded-xl border border-[var(--border)] bg-white/50 px-4 py-4 dark:bg-white/[0.03]">
        <div className="mb-3 flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--text-faint)]">
            运行来源
          </span>
          {isBound ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-[rgba(47,116,103,0.08)] px-2 py-0.5 text-[10px] font-medium text-[var(--moss)]">
              <Lock size={10} /> 已锁定
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full bg-[rgba(141,104,68,0.08)] px-2 py-0.5 text-[10px] font-medium text-[var(--text-faint)]">
              <Unlock size={10} /> 手动指定
            </span>
          )}
        </div>

        <div className="space-y-3">
          {/* 账号选择 */}
          <label className="block">
            <span className="text-[11px] font-medium text-[var(--text-soft)]">绑定账号</span>
            <select
              className="nest-field nest-r-lg mt-1.5 block w-full px-3 py-2.5 text-sm"
              value={form.accountRef}
              onChange={(event) => handleAccountChange(event.target.value)}
            >
              <option value="">不绑定账号（手动指定 Provider）</option>
              {PROVIDER_OPTIONS.map((po) => {
                const groupAccounts = accounts.filter((a) => a.protocol === po.value);
                if (groupAccounts.length === 0) return null;
                return (
                  <optgroup key={po.value} label={po.label}>
                    {groupAccounts.map((acc) => (
                      <option key={acc.id} value={acc.id}>
                        {acc.displayName}
                        {acc.authType === "api_key" ? " · API Key" : " · 订阅"}
                        {acc.models && acc.models.length > 0 ? ` · ${acc.models.length} 模型` : ""}
                      </option>
                    ))}
                  </optgroup>
                );
              })}
            </select>
            {accounts.length === 0 && (
              <p className="mt-1.5 text-xs leading-6 text-[var(--danger)]">
                没有可用账号，请先前往「AI Provider 编排」页面添加。
              </p>
            )}
          </label>

          {/* Provider — 绑定后只读 */}
          <label className="block">
            <span className="text-[11px] font-medium text-[var(--text-soft)]">Provider</span>
            {isBound ? (
              <div className="mt-1.5 flex items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--panel-soft)] px-3 py-2.5 text-sm text-[var(--text-strong)]">
                <Lock size={14} className="text-[var(--text-faint)]" />
                {PROVIDER_LABELS[form.provider] || form.provider}
                <span className="text-[var(--text-faint)]">（跟随账号）</span>
              </div>
            ) : (
              <select
                className="nest-field nest-r-lg mt-1.5 block w-full px-3 py-2.5 text-sm"
                value={form.provider}
                onChange={(event) =>
                  setForm((current) => ({ ...current, provider: event.target.value }))
                }
              >
                {PROVIDER_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            )}
          </label>

          {/* 模型选择 */}
          <label className="block">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-medium text-[var(--text-soft)]">默认模型</span>
              {isBound && availableModels.length > 0 && (
                <button
                  type="button"
                  onClick={() =>
                    setForm((current) => ({
                      ...current,
                      useCustomModel: !current.useCustomModel,
                      defaultModel: !current.useCustomModel
                        ? current.defaultModel
                        : availableModels[0] || "",
                    }))
                  }
                  className={`text-[10px] font-medium transition-colors ${
                    form.useCustomModel
                      ? "text-[var(--accent-deep)]"
                      : "text-[var(--text-faint)] hover:text-[var(--text-soft)]"
                  }`}
                >
                  {form.useCustomModel ? "使用账号模型池" : "自定义覆盖"}
                </button>
              )}
            </div>

            {isBound && availableModels.length > 0 && !form.useCustomModel ? (
              <select
                className="nest-field nest-r-lg mt-1.5 block w-full px-3 py-2.5 text-sm"
                value={form.defaultModel}
                onChange={(event) =>
                  setForm((current) => ({ ...current, defaultModel: event.target.value }))
                }
              >
                <option value="">请选择模型</option>
                {availableModels.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            ) : (
              <>
                <input
                  className="nest-field nest-r-lg mt-1.5 block w-full px-3 py-2.5 text-sm"
                  value={form.defaultModel}
                  onChange={(event) =>
                    setForm((current) => ({ ...current, defaultModel: event.target.value }))
                  }
                  placeholder={isBound ? "输入自定义模型名" : "例如 gpt-5.4"}
                  list={isBound && availableModels.length > 0 ? "model-suggestions" : undefined}
                />
                {isBound && availableModels.length > 0 && (
                  <datalist id="model-suggestions">
                    {availableModels.map((m) => (
                      <option key={m} value={m} />
                    ))}
                  </datalist>
                )}
              </>
            )}

            {isBound && boundAccount && (
              <p className="mt-1.5 text-xs leading-6 text-[var(--text-faint)]">
                已绑定 <span className="text-[var(--text-soft)]">{boundAccount.displayName}</span>
                {boundAccount.models && boundAccount.models.length > 0
                  ? ` · 账号模型池: ${boundAccount.models.join("、")}`
                  : " · 未配置模型列表"}
              </p>
            )}
          </label>
        </div>
      </div>

      {/* ── 身份资料 ── */}
      <div className="mt-4 grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <label className="block">
          <span className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--text-faint)]">
            个性与擅长
          </span>
          <textarea
            className="nest-field nest-r-xl mt-2 block min-h-[132px] w-full px-3 py-3 text-sm leading-7"
            value={form.personality}
            onChange={(event) =>
              setForm((current) => ({ ...current, personality: event.target.value }))
            }
            placeholder="用一两句话描述这只猫的气质、角色和擅长方向..."
          />
        </label>

        <div className="space-y-3">
          <label className="block">
            <span className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--text-faint)]">
              @ 提及别名
            </span>
            <input
              className="nest-field nest-r-lg mt-2 block w-full px-3 py-3 text-sm"
              value={form.mentionPatterns}
              onChange={(event) =>
                setForm((current) => ({ ...current, mentionPatterns: event.target.value }))
              }
              placeholder="@gemini, @烁烁"
            />
          </label>

          <div className="nest-card nest-r-lg border-[var(--border)]/80 bg-white/55 px-4 py-4 dark:bg-white/[0.03]">
            <div className="text-sm font-medium text-[var(--text-strong)]">当前保存规则</div>
            <div className="mt-3 space-y-2 text-xs leading-6 text-[var(--text-soft)]">
              <p>展示名称会同时作为持久化名称。</p>
              <p>@ 提及别名会自动去空格并过滤空项。</p>
              <p>绑定账号后 Provider 自动跟随，模型默认从账号池选取。</p>
            </div>
          </div>
        </div>
      </div>

      <div className="mt-5 flex flex-col gap-3 border-t border-[var(--line)] pt-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="text-xs leading-6 text-[var(--text-faint)]">
          {isEdit
            ? `当前正在编辑 ${cat?.displayName || cat?.name || cat?.id}`
            : "创建后会立即刷新猫咪列表。"}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="nest-button-ghost flex items-center gap-1 rounded-full px-4 py-2 text-sm"
          >
            <X size={14} />
            取消
          </button>
          <button
            type="button"
            onClick={() => onSave(form)}
            disabled={!canSubmit}
            className="nest-button-primary flex items-center gap-1 rounded-full px-4 py-2 text-sm font-medium disabled:opacity-50"
          >
            <Save size={14} />
            {isEdit ? "保存修改" : "创建猫咪"}
          </button>
        </div>
      </div>
    </div>
  );
}

export function CatSettings() {
  const cats = useCatStore((state) => state.cats);
  const defaultCatId = useCatStore((state) => state.defaultCatId);
  const loading = useCatStore((state) => state.loading);
  const fetchCats = useCatStore((state) => state.fetchCats);
  const createCat = useCatStore((state) => state.createCat);
  const updateCat = useCatStore((state) => state.updateCat);
  const deleteCat = useCatStore((state) => state.deleteCat);

  const bindCat = useAccountStore((state) => state.bindCat);
  const fetchAccounts = useAccountStore((state) => state.fetchAccounts);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void fetchCats();
    void fetchAccounts();
  }, [fetchCats, fetchAccounts]);

  const model = buildCatSettingsModel({ cats, defaultCatId });
  const editingCat = cats.find((cat) => cat.id === editingId);

  const handleCreate = async (draft: CatEditorState) => {
    if (!draft.id.trim()) {
      setError("请先填写猫咪 ID");
      return;
    }

    try {
      setError(null);
      const payload = buildCatMutationPayload(draft);
      const cat = await createCat({
        id: draft.id.trim(),
        ...payload,
      });
      if (draft.accountRef) {
        await bindCat(cat.id, draft.accountRef);
      }
      setShowCreate(false);
    } catch (error: unknown) {
      setError(getErrorMessage(error));
    }
  };

  const handleUpdate = async (catId: string, draft: CatEditorState) => {
    try {
      setError(null);
      const payload = buildCatMutationPayload(draft);
      await updateCat(catId, payload);
      if (draft.accountRef) {
        await bindCat(catId, draft.accountRef);
      }
      setEditingId(null);
    } catch (error: unknown) {
      setError(getErrorMessage(error));
    }
  };

  const handleDelete = async (cat: Cat) => {
    if (!confirm(`确定删除猫咪 "${cat.displayName || cat.name}"？`)) {
      return;
    }

    try {
      setError(null);
      await deleteCat(cat.id);
    } catch (error: unknown) {
      setError(getErrorMessage(error));
    }
  };

  if (loading && cats.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-[var(--accent)]" />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <SettingsSummaryGrid items={model.summaryCards} />

      <SettingsSectionCard
        eyebrow="Identity Roster"
        title="猫咪管理"
        description="管理猫咪身份、个性和运行来源。新增或编辑时先选账号，Provider 和模型自动跟随。"
        actions={
          <button
            type="button"
            onClick={() => {
              setShowCreate(true);
              setEditingId(null);
            }}
            className="nest-button-primary flex items-center gap-1 rounded-full px-4 py-2 text-sm font-medium"
          >
            <Plus size={14} />
            添加猫咪
          </button>
        }
      >
        <div className="space-y-4">
          {error && (
            <div className="nest-r-lg border border-[rgba(164,70,42,0.24)] bg-[rgba(164,70,42,0.08)] px-4 py-3 text-sm text-[var(--danger)]">
              <div className="flex items-start justify-between gap-3">
                <span>{error}</span>
                <button
                  type="button"
                  onClick={() => setError(null)}
                  className="text-[var(--danger)]/80 transition-opacity hover:opacity-80"
                >
                  <X size={14} />
                </button>
              </div>
            </div>
          )}

          {showCreate && <CatEditor onSave={handleCreate} onCancel={() => setShowCreate(false)} />}

          {editingCat && (
            <CatEditor
              cat={editingCat}
              onSave={(draft) => handleUpdate(editingCat.id, draft)}
              onCancel={() => setEditingId(null)}
            />
          )}

          {model.entries.length === 0 ? (
            <div className="nest-r-xl border border-dashed border-[var(--border)] bg-white/45 px-5 py-10 text-center dark:bg-white/[0.03]">
              <div className="text-sm font-medium text-[var(--text-strong)]">还没有猫咪档案</div>
              <p className="mt-2 text-sm leading-7 text-[var(--text-soft)]">
                先创建第一只猫，把展示名称、Provider、绑定账号和模型设出来，后面的权限和调度才有稳定身份基线。
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {model.entries.map((entry) => {
                const sourceCat = cats.find((cat) => cat.id === entry.id);
                return (
                  <article
                    key={entry.id}
                    className={`group flex items-start gap-4 rounded-2xl border px-4 py-3.5 transition-colors ${
                      entry.isDefault
                        ? "border-[rgba(183,103,37,0.18)] bg-[rgba(255,247,236,0.6)] dark:bg-[rgba(57,41,31,0.5)]"
                        : "border-[var(--border)] bg-white/50 dark:bg-white/[0.03]"
                    }`}
                  >
                    {/* avatar */}
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[var(--accent-soft)] text-[var(--accent-deep)] dark:text-[var(--accent)]">
                      <Bot size={16} />
                    </div>

                    {/* main content */}
                    <div className="min-w-0 flex-1 space-y-1.5">
                      {/* line 1: name + meta + status badges */}
                      <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
                        <span className="font-semibold text-[var(--text-strong)]">
                          {entry.title}
                        </span>
                        <span className="text-[var(--text-faint)]">{entry.metaLabel}</span>
                        {entry.isDefault && (
                          <span className="rounded-full bg-[rgba(183,103,37,0.1)] px-2 py-0.5 text-[11px] font-medium text-[var(--accent-deep)] dark:bg-[rgba(230,162,93,0.12)] dark:text-[var(--accent)]">
                            默认
                          </span>
                        )}
                        <span
                          className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
                            entry.isAvailable
                              ? "bg-[rgba(47,116,103,0.08)] text-[var(--moss)]"
                              : "bg-[rgba(141,104,68,0.08)] text-[var(--text-faint)]"
                          }`}
                        >
                          {entry.availabilityLabel}
                        </span>
                        {sourceCat?.accountRef && (
                          <AccountBadge accountId={sourceCat.accountRef} />
                        )}
                      </div>

                      {/* line 2: personality preview */}
                      {entry.personalityPreview && (
                        <p className="text-sm leading-relaxed text-[var(--text-soft)]">
                          {entry.personalityPreview}
                        </p>
                      )}

                      {/* line 3: model + role */}
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-[var(--text-faint)]">
                        <span>
                          模型{" "}
                          <span
                            className={
                              entry.attentionReasons.includes("未配置默认模型")
                                ? "text-[var(--danger)]"
                                : "text-[var(--text-soft)]"
                            }
                          >
                            {entry.defaultModelLabel}
                          </span>
                        </span>
                        {entry.roleSummary && <span>{entry.roleSummary}</span>}
                      </div>

                      {/* line 4: mention aliases */}
                      {entry.mentionPatterns.length > 0 && (
                        <div className="text-xs text-[var(--text-faint)]">
                          提及{" "}
                          <span className="text-[var(--text-soft)]">
                            {entry.mentionPatterns.join(" · ")}
                          </span>
                        </div>
                      )}

                      {/* attention note */}
                      {entry.attentionSummary && (
                        <p className="text-xs text-[var(--danger)]/80">{entry.attentionSummary}</p>
                      )}
                    </div>

                    {/* actions */}
                    <div className="flex shrink-0 items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                      <button
                        type="button"
                        onClick={() => {
                          setEditingId(entry.id);
                          setShowCreate(false);
                        }}
                        className="flex h-8 w-8 items-center justify-center rounded-full text-[var(--text-faint)] transition-colors hover:bg-[var(--accent-soft)] hover:text-[var(--text-strong)]"
                        title="编辑"
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        type="button"
                        onClick={() => sourceCat && void handleDelete(sourceCat)}
                        className="flex h-8 w-8 items-center justify-center rounded-full text-[var(--text-faint)] transition-colors hover:bg-[rgba(164,70,42,0.08)] hover:text-[var(--danger)]"
                        title="删除"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </div>
      </SettingsSectionCard>
    </div>
  );
}
