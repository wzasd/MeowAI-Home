import { useAccountStore } from "../../stores/accountStore";
import { useCatStore, type Cat } from "../../stores/catStore";
import { useEffect, useState } from "react";
import {
  Loader2,
  Plus,
  Trash2,
  Key,
  Check,
  X,
  Save,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Bot,
  ArrowRight,
} from "lucide-react";
import type { AccountResponse, AuthType, Protocol } from "../../types";

interface AccountFormPayload {
  id?: string;
  displayName: string;
  protocol: Protocol;
  authType: AuthType;
  baseUrl?: string;
  models?: string[];
  apiKey?: string;
}

const PROTOCOL_LABELS: Record<string, string> = {
  anthropic: "Anthropic",
  openai: "OpenAI",
  google: "Google",
  opencode: "OpenCode",
};

const PROTOCOL_ORDER: Protocol[] = ["anthropic", "openai", "google", "opencode"];

/* ────────── 辅助函数 ────────── */

function groupAccountsByProtocol(accounts: AccountResponse[]): Map<Protocol, AccountResponse[]> {
  const map = new Map<Protocol, AccountResponse[]>();
  for (const p of PROTOCOL_ORDER) map.set(p, []);
  for (const acc of accounts) {
    const list = map.get(acc.protocol);
    if (list) list.push(acc);
  }
  return map;
}

function getBoundCats(accountId: string, cats: Cat[]): Cat[] {
  return cats.filter((c) => c.accountRef === accountId);
}

interface Anomaly {
  type: "unbound" | "protocol-mismatch" | "model-outside-pool";
  catId: string;
  catName: string;
  detail: string;
}

function computeAnomalies(cats: Cat[], accounts: AccountResponse[]): Anomaly[] {
  const anomalies: Anomaly[] = [];
  for (const cat of cats) {
    if (!cat.accountRef) {
      anomalies.push({
        type: "unbound",
        catId: cat.id,
        catName: cat.displayName || cat.name,
        detail: "未绑定任何账号",
      });
      continue;
    }
    const account = accounts.find((a) => a.id === cat.accountRef);
    if (!account) {
      anomalies.push({
        type: "unbound",
        catId: cat.id,
        catName: cat.displayName || cat.name,
        detail: `绑定的账号 ${cat.accountRef} 已不存在`,
      });
      continue;
    }
    if (cat.provider !== account.protocol) {
      anomalies.push({
        type: "protocol-mismatch",
        catId: cat.id,
        catName: cat.displayName || cat.name,
        detail: `猫 Provider 为 ${cat.provider}，但绑定账号协议为 ${account.protocol}`,
      });
    }
    if (account.models && account.models.length > 0 && cat.defaultModel) {
      if (!account.models.includes(cat.defaultModel)) {
        anomalies.push({
          type: "model-outside-pool",
          catId: cat.id,
          catName: cat.displayName || cat.name,
          detail: `模型 ${cat.defaultModel} 不在账号模型池内`,
        });
      }
    }
  }
  return anomalies;
}

/* ────────── 编排摘要带 ────────── */

function OrchestrationSummary({
  accounts,
  cats,
}: {
  accounts: AccountResponse[];
  cats: Cat[];
}) {
  const enabledProviders = new Set(accounts.map((a) => a.protocol)).size;
  const totalAccounts = accounts.length;
  const boundCats = cats.filter((c) => c.accountRef).length;
  const unboundCats = cats.length - boundCats;
  const anomalies = computeAnomalies(cats, accounts);

  return (
    <div className="space-y-2 rounded-2xl border border-[var(--border)] bg-white/60 px-5 py-4 dark:bg-white/[0.04]">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
        <span className="text-[var(--text-strong)]">
          已启用 <strong className="text-[var(--accent-deep)]">{enabledProviders}</strong> 个 Provider
        </span>
        <span className="text-[var(--text-faint)]">·</span>
        <span className="text-[var(--text-strong)]">
          <strong className="text-[var(--accent-deep)]">{totalAccounts}</strong> 个账号可用
        </span>
        <span className="text-[var(--text-faint)]">·</span>
        <span className="text-[var(--text-strong)]">
          <strong className="text-[var(--moss)]">{boundCats}</strong> 只猫已绑定
          {unboundCats > 0 && (
            <span className="text-[var(--danger)]"> / {unboundCats} 只未绑定</span>
          )}
        </span>
        {anomalies.length > 0 && (
          <>
            <span className="text-[var(--text-faint)]">·</span>
            <span className="inline-flex items-center gap-1 text-[var(--danger)]">
              <AlertTriangle size={14} />
              {anomalies.length} 项异常待处理
            </span>
          </>
        )}
      </div>
    </div>
  );
}

/* ────────── Provider 分段 ────────── */

function ProviderSection({
  protocol,
  accounts,
  cats,
  onDelete,
  onEdit,
  onBindCat,
}: {
  protocol: Protocol;
  accounts: AccountResponse[];
  cats: Cat[];
  onDelete: (id: string) => void;
  onEdit: (acc: AccountResponse) => void;
  onBindCat: (catId: string, accountId: string) => void;
}) {
  const [expandedModels, setExpandedModels] = useState<Record<string, boolean>>({});
  const [expandedCats, setExpandedCats] = useState<Record<string, boolean>>({});
  const unboundCats = cats.filter((c) => !c.accountRef);

  const toggleModels = (id: string) =>
    setExpandedModels((p) => ({ ...p, [id]: !p[id] }));
  const toggleCats = (id: string) =>
    setExpandedCats((p) => ({ ...p, [id]: !p[id] }));

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-white/55 dark:bg-white/[0.03]">
      {/* Section header */}
      <div className="flex items-center gap-3 border-b border-[var(--line)] px-5 py-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-[var(--accent-soft)] text-[var(--accent-deep)] dark:text-[var(--accent)]">
          <Key size={16} />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-[var(--text-strong)]">
            {PROTOCOL_LABELS[protocol] || protocol}
          </h3>
          <p className="text-xs text-[var(--text-faint)]">
            {accounts.length} 个账号 · {accounts.reduce((sum, a) => sum + getBoundCats(a.id, cats).length, 0)} 只猫已绑定
          </p>
        </div>
      </div>

      {/* Account rows */}
      <div className="divide-y divide-[var(--line)]">
        {accounts.map((account) => {
          const bound = getBoundCats(account.id, cats);
          const modelsOpen = expandedModels[account.id];
          const catsOpen = expandedCats[account.id];

          return (
            <div key={account.id} className="px-5 py-3">
              {/* Row 1: account identity + actions */}
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                    <span className="text-sm font-medium text-[var(--text-strong)]">
                      {account.displayName}
                    </span>
                    {account.isBuiltin && (
                      <span className="rounded-full bg-[rgba(183,103,37,0.08)] px-2 py-0.5 text-[10px] font-medium text-[var(--accent-deep)] dark:bg-[rgba(230,162,93,0.1)]">
                        内置
                      </span>
                    )}
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                        account.authType === "api_key"
                          ? "bg-indigo-50 text-indigo-600 dark:bg-indigo-900/20 dark:text-indigo-400"
                          : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400"
                      }`}
                    >
                      {account.authType === "api_key" ? "API Key" : "订阅"}
                    </span>
                    {account.authType === "api_key" &&
                      (account.hasApiKey ? (
                        <ShieldCheck size={12} className="text-green-500" />
                      ) : (
                        <X size={12} className="text-red-500" />
                      ))}
                  </div>
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-[var(--text-faint)]">
                    {account.baseUrl && <span>{account.baseUrl}</span>}
                    {account.models && account.models.length > 0 && (
                      <span>{account.models.length} 个模型</span>
                    )}
                    {bound.length > 0 && (
                      <span className="text-[var(--moss)]">{bound.length} 只猫已绑定</span>
                    )}
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  <button
                    onClick={() => onEdit(account)}
                    className="flex h-7 w-7 items-center justify-center rounded-full text-[var(--text-faint)] transition-colors hover:bg-[var(--accent-soft)] hover:text-[var(--text-strong)]"
                    title="编辑"
                  >
                    <Save size={13} />
                  </button>
                  {!account.isBuiltin && (
                    <button
                      onClick={() => onDelete(account.id)}
                      className="flex h-7 w-7 items-center justify-center rounded-full text-[var(--text-faint)] transition-colors hover:bg-[rgba(164,70,42,0.08)] hover:text-[var(--danger)]"
                      title="删除"
                    >
                      <Trash2 size={13} />
                    </button>
                  )}
                </div>
              </div>

              {/* Row 2: expandable model list */}
              {account.models && account.models.length > 0 && (
                <div className="mt-2">
                  <button
                    onClick={() => toggleModels(account.id)}
                    className="inline-flex items-center gap-1 text-xs text-[var(--text-faint)] transition-colors hover:text-[var(--text-soft)]"
                  >
                    {modelsOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                    可用模型
                  </button>
                  {modelsOpen && (
                    <div className="mt-1.5 flex flex-wrap gap-1.5">
                      {account.models.map((m) => (
                        <span
                          key={m}
                          className="inline-flex items-center rounded-full border border-[var(--border)] bg-white/70 px-2.5 py-0.5 text-[11px] text-[var(--text-soft)] dark:bg-white/[0.04]"
                        >
                          {m}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Row 3: bound cats + bind more */}
              <div className="mt-2">
                <button
                  onClick={() => toggleCats(account.id)}
                  className="inline-flex items-center gap-1 text-xs text-[var(--text-faint)] transition-colors hover:text-[var(--text-soft)]"
                >
                  {catsOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                  已绑定猫咪
                </button>
                {catsOpen && (
                  <div className="mt-1.5 space-y-2">
                    {bound.length > 0 ? (
                      <div className="flex flex-wrap gap-2">
                        {bound.map((cat) => (
                          <span
                            key={cat.id}
                            className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-1 text-xs text-blue-700 dark:bg-blue-900/20 dark:text-blue-400"
                          >
                            <Bot size={10} />
                            {cat.displayName || cat.name}
                            {cat.defaultModel && (
                              <span className="text-blue-500/60">· {cat.defaultModel}</span>
                            )}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-[var(--text-faint)]">暂无猫咪绑定</p>
                    )}
                    {/* Quick bind unbound cats */}
                    {unboundCats.length > 0 && (
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] text-[var(--text-faint)]">绑定更多:</span>
                        <select
                          className="rounded-lg border border-[var(--border)] bg-white/70 px-2 py-1 text-[11px] text-[var(--text-soft)] dark:bg-white/[0.04]"
                          defaultValue=""
                          onChange={(e) => {
                            if (e.target.value) {
                              onBindCat(e.target.value, account.id);
                              e.target.value = "";
                            }
                          }}
                        >
                          <option value="">选择猫咪...</option>
                          {unboundCats.map((cat) => (
                            <option key={cat.id} value={cat.id}>
                              {cat.displayName || cat.name}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {accounts.length === 0 && (
        <div className="px-5 py-6 text-center">
          <p className="text-xs text-[var(--text-faint)]">该 Provider 下暂无账号</p>
        </div>
      )}
    </div>
  );
}

/* ────────── 异常队列 ────────── */

function AnomalyQueue({ anomalies }: { anomalies: Anomaly[] }) {
  if (anomalies.length === 0) return null;

  return (
    <div className="rounded-2xl border border-[rgba(164,70,42,0.18)] bg-[rgba(164,70,42,0.04)] px-5 py-4 dark:bg-[rgba(164,70,42,0.06)]">
      <div className="flex items-center gap-2 text-sm font-medium text-[var(--danger)]">
        <AlertTriangle size={16} />
        待处理队列 · {anomalies.length} 项异常
      </div>
      <div className="mt-3 space-y-2">
        {anomalies.map((a) => (
          <div
            key={`${a.type}-${a.catId}`}
            className="flex items-center gap-3 rounded-xl border border-[rgba(164,70,42,0.1)] bg-white/60 px-3 py-2 text-xs dark:bg-white/[0.03]"
          >
            <Bot size={14} className="shrink-0 text-[var(--text-faint)]" />
            <span className="font-medium text-[var(--text-strong)]">{a.catName}</span>
            <ArrowRight size={12} className="text-[var(--text-faint)]" />
            <span className="text-[var(--danger)]">{a.detail}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ────────── 账号编辑器 ────────── */

function AccountEditor({
  account,
  onSave,
  onCancel,
}: {
  account?: AccountResponse;
  onSave: (data: AccountFormPayload) => void;
  onCancel: () => void;
}) {
  const store = useAccountStore();
  const [form, setForm] = useState({
    id: "",
    displayName: account?.displayName || "",
    protocol: (account?.protocol || "anthropic") as Protocol,
    authType: (account?.authType || "api_key") as AuthType,
    baseUrl: account?.baseUrl || "",
    apiKey: "",
    models: account?.models?.join(", ") || "",
  });
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<boolean | null>(null);
  const isEdit = !!account;

  const handleTestKey = async () => {
    if (!form.apiKey) return;
    setTesting(true);
    setTestResult(null);
    try {
      const valid = await store.testKey(
        account?.id || "__new__",
        form.apiKey,
        form.protocol,
        form.baseUrl || undefined
      );
      setTestResult(valid);
    } catch {
      setTestResult(false);
    }
    setTesting(false);
  };

  return (
    <div className="space-y-3 rounded-[1.35rem] border border-[rgba(47,116,103,0.18)] bg-[linear-gradient(145deg,rgba(247,243,233,0.88),rgba(255,255,255,0.72))] p-5 shadow-[0_24px_60px_-40px_rgba(15,23,42,0.55)] dark:bg-[rgba(18,24,29,0.92)]">
      {!isEdit && (
        <label className="block">
          <span className="text-xs font-medium text-gray-700 dark:text-gray-300">账号 ID</span>
          <input
            className="mt-1 block w-full rounded border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            value={form.id}
            onChange={(e) => setForm((f) => ({ ...f, id: e.target.value }))}
            placeholder="例如 my-anthropic-key"
          />
        </label>
      )}
      <div className="grid grid-cols-2 gap-3">
        <label className="block">
          <span className="text-xs font-medium text-gray-700 dark:text-gray-300">显示名称</span>
          <input
            className="mt-1 block w-full rounded border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            value={form.displayName}
            onChange={(e) => setForm((f) => ({ ...f, displayName: e.target.value }))}
            placeholder="我的 Anthropic 账号"
          />
        </label>
        <label className="block">
          <span className="text-xs font-medium text-gray-700 dark:text-gray-300">协议</span>
          <select
            className="mt-1 block w-full rounded border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            value={form.protocol}
            onChange={(e) => setForm((f) => ({ ...f, protocol: e.target.value as Protocol }))}
          >
            <option value="anthropic">Anthropic</option>
            <option value="openai">OpenAI</option>
            <option value="google">Google</option>
            <option value="opencode">OpenCode</option>
          </select>
        </label>
      </div>
      <label className="block">
        <span className="text-xs font-medium text-gray-700 dark:text-gray-300">认证方式</span>
        <select
          className="mt-1 block w-full rounded border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
          value={form.authType}
          onChange={(e) => setForm((f) => ({ ...f, authType: e.target.value as AuthType }))}
        >
          <option value="api_key">API Key</option>
          <option value="subscription">订阅授权（CLI OAuth）</option>
        </select>
      </label>
      {form.authType === "api_key" && (
        <>
          <label className="block">
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">API Key</span>
            <div className="mt-1 flex gap-2">
              <input
                type="password"
                className="block w-full rounded border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                value={form.apiKey}
                onChange={(e) => setForm((f) => ({ ...f, apiKey: e.target.value }))}
                placeholder="sk-..."
              />
              <button
                onClick={handleTestKey}
                disabled={!form.apiKey || testing}
                className="flex items-center gap-1 rounded bg-gray-100 px-3 py-1.5 text-xs font-medium hover:bg-gray-200 disabled:opacity-50 dark:bg-gray-700 dark:hover:bg-gray-600"
              >
                {testing ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : testResult === true ? (
                  <Check size={12} className="text-green-500" />
                ) : testResult === false ? (
                  <X size={12} className="text-red-500" />
                ) : null}
                测试密钥
              </button>
            </div>
          </label>
          <label className="block">
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
              Base URL（可选）
            </span>
            <input
              className="mt-1 block w-full rounded border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              value={form.baseUrl}
              onChange={(e) => setForm((f) => ({ ...f, baseUrl: e.target.value }))}
              placeholder="https://api.anthropic.com"
            />
          </label>
        </>
      )}
      <label className="block">
        <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
          模型列表（逗号分隔，可选）
        </span>
        <input
          className="mt-1 block w-full rounded border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
          value={form.models}
          onChange={(e) => setForm((f) => ({ ...f, models: e.target.value }))}
          placeholder="claude-sonnet-4-6, claude-opus-4-6"
        />
      </label>
      <div className="flex justify-end gap-2">
        <button
          onClick={onCancel}
          className="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700"
        >
          取消
        </button>
        <button
          onClick={() => {
            onSave({
              id: form.id || undefined,
              displayName: form.displayName,
              protocol: form.protocol,
              authType: form.authType,
              baseUrl: form.baseUrl || undefined,
              models: form.models
                ? form.models
                    .split(",")
                    .map((s) => s.trim())
                    .filter(Boolean)
                : undefined,
              apiKey: form.apiKey || undefined,
            });
          }}
          className="flex items-center gap-1 rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          <Save size={14} />
          {isEdit ? "保存修改" : "创建账号"}
        </button>
      </div>
    </div>
  );
}

/* ────────── 主页面 ────────── */

export function AccountSettings() {
  const accounts = useAccountStore((s) => s.accounts);
  const loading = useAccountStore((s) => s.loading);
  const fetchAccounts = useAccountStore((s) => s.fetchAccounts);
  const createAccount = useAccountStore((s) => s.createAccount);
  const updateAccount = useAccountStore((s) => s.updateAccount);
  const deleteAccount = useAccountStore((s) => s.deleteAccount);
  const bindCat = useAccountStore((s) => s.bindCat);

  const cats = useCatStore((s) => s.cats);
  const fetchCats = useCatStore((s) => s.fetchCats);

  const [showEditor, setShowEditor] = useState(false);
  const [editingAccount, setEditingAccount] = useState<AccountResponse | null>(null);

  useEffect(() => {
    void fetchAccounts();
    void fetchCats();
  }, [fetchAccounts, fetchCats]);

  const grouped = groupAccountsByProtocol(accounts);
  const anomalies = computeAnomalies(cats, accounts);

  const handleCreate = async (data: AccountFormPayload) => {
    if (!data.id) return;
    await createAccount({ ...data, id: data.id });
    setShowEditor(false);
  };

  const handleUpdate = async (data: AccountFormPayload) => {
    if (!editingAccount) return;
    const payload: Record<string, unknown> = { ...data };
    await updateAccount(editingAccount.id, payload);
    setEditingAccount(null);
  };

  const handleDelete = async (id: string) => {
    if (confirm("确定删除该账号？已绑定的猫咪将变为未绑定状态。")) {
      await deleteAccount(id);
    }
  };

  const handleBindCat = async (catId: string, accountId: string) => {
    await bindCat(catId, accountId);
  };

  if (loading && accounts.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* 编排摘要带 */}
      <OrchestrationSummary accounts={accounts} cats={cats} />

      {/* 新增账号按钮 */}
      <div className="flex justify-end">
        <button
          onClick={() => {
            setShowEditor(true);
            setEditingAccount(null);
          }}
          className="nest-button-primary flex items-center gap-1 rounded-full px-4 py-2 text-sm font-medium"
        >
          <Plus size={14} />
          新增账号
        </button>
      </div>

      {/* 编辑器 */}
      {showEditor && !editingAccount && (
        <AccountEditor onSave={handleCreate} onCancel={() => setShowEditor(false)} />
      )}
      {editingAccount && (
        <AccountEditor
          account={editingAccount}
          onSave={(data) => handleUpdate(data)}
          onCancel={() => setEditingAccount(null)}
        />
      )}

      {/* Provider 分段编排 */}
      <div className="space-y-4">
        {PROTOCOL_ORDER.map((protocol) => {
          const list = grouped.get(protocol) || [];
          if (list.length === 0) return null;
          return (
            <ProviderSection
              key={protocol}
              protocol={protocol}
              accounts={list}
              cats={cats}
              onDelete={handleDelete}
              onEdit={(acc) => {
                setEditingAccount(acc);
                setShowEditor(false);
              }}
              onBindCat={handleBindCat}
            />
          );
        })}
      </div>

      {/* 异常队列 */}
      <AnomalyQueue anomalies={anomalies} />

      {/* 空状态 */}
      {accounts.length === 0 && (
        <div className="rounded-2xl border border-dashed border-[var(--border)] bg-white/45 px-5 py-10 text-center dark:bg-white/[0.03]">
          <div className="text-sm font-medium text-[var(--text-strong)]">
            还没有 Provider 账号
          </div>
          <p className="mt-2 text-sm leading-7 text-[var(--text-soft)]">
            先创建可用账号，配置认证方式和模型列表，再把猫咪绑定到对应通道上。
          </p>
        </div>
      )}
    </div>
  );
}
