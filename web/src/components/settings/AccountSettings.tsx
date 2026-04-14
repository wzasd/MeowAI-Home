import { useAccountStore } from "../../stores/accountStore";
import { useCatStore, type Cat } from "../../stores/catStore";
import { useEffect, useState } from "react";
import { Loader2, Plus, Trash2, Key, Check, X, Save, ShieldCheck } from "lucide-react";
import type { AccountResponse, AuthType, Protocol } from "../../types";

const PROTOCOL_LABELS: Record<string, string> = {
  anthropic: "Anthropic",
  openai: "OpenAI",
  google: "Google",
  opencode: "OpenCode",
};

const PROTOCOL_COLORS: Record<string, string> = {
  anthropic: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  openai: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  google: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  opencode: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
};

function AccountCard({
  account,
  cats,
  onDelete,
  onEdit,
  onBindCat,
}: {
  account: AccountResponse;
  cats: Cat[];
  onDelete: () => void;
  onEdit: () => void;
  onBindCat: (catId: string) => void;
}) {
  const boundCats = cats.filter((c) => c.accountRef === account.id);
  const unboundCats = cats.filter((c) => c.accountRef !== account.id);

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-700">
            <Key size={20} className="text-gray-500 dark:text-gray-400" />
          </div>
          <div>
            <h4 className="font-medium text-gray-900 dark:text-gray-100">{account.displayName}</h4>
            <div className="mt-1 flex items-center gap-2">
              <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${PROTOCOL_COLORS[account.protocol] || "bg-gray-100 text-gray-600"}`}>
                {PROTOCOL_LABELS[account.protocol] || account.protocol}
              </span>
              <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${
                account.authType === "subscription"
                  ? "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400"
                  : "bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400"
              }`}>
                {account.authType === "subscription" ? "Subscription" : "API Key"}
              </span>
              {account.authType === "api_key" && (
                account.hasApiKey
                  ? <ShieldCheck size={14} className="text-green-500" />
                  : <X size={14} className="text-red-500" />
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={onEdit} className="rounded p-1.5 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700" title="Edit">
            <Save size={14} />
          </button>
          {!account.isBuiltin && (
            <button onClick={onDelete} className="rounded p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20" title="Delete">
              <Trash2 size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Bound cats */}
      {boundCats.length > 0 && (
        <div className="mt-3 border-t border-gray-100 pt-3 dark:border-gray-700">
          <span className="text-xs text-gray-500 dark:text-gray-400">Bound cats:</span>
          <div className="mt-1 flex flex-wrap gap-1">
            {boundCats.map((cat) => (
              <span key={cat.id} className="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                {cat.displayName || cat.name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Bind additional cat */}
      {unboundCats.length > 0 && (
        <div className="mt-2">
          <select
            className="rounded border border-gray-200 bg-white px-2 py-1 text-xs dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            defaultValue=""
            onChange={(e) => { if (e.target.value) onBindCat(e.target.value); }}
          >
            <option value="">Bind a cat...</option>
            {unboundCats.map((cat) => (
              <option key={cat.id} value={cat.id}>{cat.displayName || cat.name}</option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
}

function AccountEditor({
  account,
  onSave,
  onCancel,
}: {
  account?: AccountResponse;
  onSave: (data: {
    id?: string;
    displayName: string;
    protocol: Protocol;
    authType: AuthType;
    baseUrl?: string;
    models?: string[];
    apiKey?: string;
  }) => void;
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
      const valid = await store.testKey(account?.id || "__new__", form.apiKey, form.protocol, form.baseUrl || undefined);
      setTestResult(valid);
    } catch {
      setTestResult(false);
    }
    setTesting(false);
  };

  return (
    <div className="space-y-3 rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-900/20">
      {!isEdit && (
        <label className="block">
          <span className="text-xs font-medium text-gray-700 dark:text-gray-300">Account ID</span>
          <input
            className="mt-1 block w-full rounded border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            value={form.id}
            onChange={(e) => setForm((f) => ({ ...f, id: e.target.value }))}
            placeholder="e.g. my-anthropic-key"
          />
        </label>
      )}
      <div className="grid grid-cols-2 gap-3">
        <label className="block">
          <span className="text-xs font-medium text-gray-700 dark:text-gray-300">Display Name</span>
          <input
            className="mt-1 block w-full rounded border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            value={form.displayName}
            onChange={(e) => setForm((f) => ({ ...f, displayName: e.target.value }))}
            placeholder="My Anthropic Key"
          />
        </label>
        <label className="block">
          <span className="text-xs font-medium text-gray-700 dark:text-gray-300">Protocol</span>
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
        <span className="text-xs font-medium text-gray-700 dark:text-gray-300">Auth Type</span>
        <select
          className="mt-1 block w-full rounded border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
          value={form.authType}
          onChange={(e) => setForm((f) => ({ ...f, authType: e.target.value as AuthType }))}
        >
          <option value="api_key">API Key</option>
          <option value="subscription">Subscription (CLI OAuth)</option>
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
                {testing ? <Loader2 size={12} className="animate-spin" /> : testResult === true ? <Check size={12} className="text-green-500" /> : testResult === false ? <X size={12} className="text-red-500" /> : null}
                Test
              </button>
            </div>
          </label>
          <label className="block">
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">Base URL (optional)</span>
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
        <span className="text-xs font-medium text-gray-700 dark:text-gray-300">Models (comma-separated, optional)</span>
        <input
          className="mt-1 block w-full rounded border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
          value={form.models}
          onChange={(e) => setForm((f) => ({ ...f, models: e.target.value }))}
          placeholder="claude-sonnet-4-6, claude-opus-4-6"
        />
      </label>
      <div className="flex justify-end gap-2">
        <button onClick={onCancel} className="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700">
          Cancel
        </button>
        <button
          onClick={() => {
            onSave({
              id: form.id || undefined,
              displayName: form.displayName,
              protocol: form.protocol,
              authType: form.authType,
              baseUrl: form.baseUrl || undefined,
              models: form.models ? form.models.split(",").map((s) => s.trim()).filter(Boolean) : undefined,
              apiKey: form.apiKey || undefined,
            });
          }}
          className="flex items-center gap-1 rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          <Save size={14} />
          {isEdit ? "Update" : "Create"}
        </button>
      </div>
    </div>
  );
}

export function AccountSettings() {
  const store = useAccountStore();
  const catStore = useCatStore();
  const [showEditor, setShowEditor] = useState(false);
  const [editingAccount, setEditingAccount] = useState<AccountResponse | null>(null);

  useEffect(() => {
    store.fetchAccounts();
    if (catStore.cats.length === 0) catStore.fetchCats();
  }, []);

  const handleCreate = async (data: {
    id?: string; displayName: string; protocol: Protocol; authType: AuthType;
    baseUrl?: string; models?: string[]; apiKey?: string;
  }) => {
    if (!data.id) return;
    await store.createAccount(data as any);
    setShowEditor(false);
  };

  const handleUpdate = async (data: Record<string, unknown>) => {
    if (!editingAccount) return;
    await store.updateAccount(editingAccount.id, data);
    setEditingAccount(null);
  };

  const handleDelete = async (id: string) => {
    if (confirm("Delete this account?")) {
      await store.deleteAccount(id);
    }
  };

  if (store.loading && store.accounts.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Configure AI provider accounts. Use API keys for independent quota, or subscription for CLI OAuth.
          </p>
        </div>
        <button
          onClick={() => { setShowEditor(true); setEditingAccount(null); }}
          className="flex items-center gap-1 rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700"
        >
          <Plus size={14} />
          Add Account
        </button>
      </div>

      {showEditor && !editingAccount && (
        <AccountEditor
          onSave={handleCreate}
          onCancel={() => setShowEditor(false)}
        />
      )}

      {editingAccount && (
        <AccountEditor
          account={editingAccount}
          onSave={(data) => handleUpdate(data)}
          onCancel={() => setEditingAccount(null)}
        />
      )}

      <div className="grid gap-3">
        {store.accounts.map((account) => (
          <AccountCard
            key={account.id}
            account={account}
            cats={catStore.cats}
            onDelete={() => handleDelete(account.id)}
            onEdit={() => { setEditingAccount(account); setShowEditor(false); }}
            onBindCat={(catId) => store.bindCat(catId, account.id)}
          />
        ))}
      </div>
    </div>
  );
}
