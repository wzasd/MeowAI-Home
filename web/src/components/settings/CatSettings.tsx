import { useCatStore, type Cat } from "../../stores/catStore";
import { useEffect, useState } from "react";
import { Loader2, Check, X, Pencil, Trash2, Plus, Save } from "lucide-react";

/** Cat editor form — used for both create and edit. */
function CatEditor({
  cat,
  onSave,
  onCancel,
}: {
  cat?: Cat;
  onSave: (data: {
    id?: string;
    name: string;
    displayName: string;
    provider: string;
    defaultModel: string;
    personality: string;
    mentionPatterns: string[];
  }) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState({
    id: cat?.id || "",
    name: cat?.displayName || cat?.name || "",
    displayName: cat?.displayName || cat?.name || "",
    provider: cat?.provider || "anthropic",
    defaultModel: cat?.defaultModel || "",
    personality: cat?.personality || "",
    mentionPatterns: (cat?.mentionPatterns || []).join(", "),
  });

  const isEdit = !!cat;

  return (
    <div className="space-y-3 rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-900/20">
      {!isEdit && (
        <label className="block">
          <span className="text-xs font-medium text-gray-700 dark:text-gray-300">ID</span>
          <input
            className="mt-1 block w-full rounded border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            value={form.id}
            onChange={(e) => setForm((f) => ({ ...f, id: e.target.value }))}
            placeholder="e.g. tabby"
          />
        </label>
      )}
      <div className="grid grid-cols-2 gap-3">
        <label className="block">
          <span className="text-xs font-medium text-gray-700 dark:text-gray-300">名称</span>
          <input
            className="mt-1 block w-full rounded border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            value={form.name}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value, displayName: e.target.value }))}
          />
        </label>
        <label className="block">
          <span className="text-xs font-medium text-gray-700 dark:text-gray-300">Provider</span>
          <select
            className="mt-1 block w-full rounded border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            value={form.provider}
            onChange={(e) => setForm((f) => ({ ...f, provider: e.target.value }))}
          >
            <option value="anthropic">Anthropic (Claude)</option>
            <option value="openai">OpenAI (GPT)</option>
            <option value="google">Google (Gemini)</option>
            <option value="dare">Dare (Deterministic)</option>
          </select>
        </label>
      </div>
      <label className="block">
        <span className="text-xs font-medium text-gray-700 dark:text-gray-300">模型</span>
        <input
          className="mt-1 block w-full rounded border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
          value={form.defaultModel}
          onChange={(e) => setForm((f) => ({ ...f, defaultModel: e.target.value }))}
          placeholder="e.g. claude-sonnet-4-6"
        />
      </label>
      <label className="block">
        <span className="text-xs font-medium text-gray-700 dark:text-gray-300">个性</span>
        <textarea
          className="mt-1 block w-full rounded border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
          rows={2}
          value={form.personality}
          onChange={(e) => setForm((f) => ({ ...f, personality: e.target.value }))}
          placeholder="描述猫咪的性格和专长..."
        />
      </label>
      <label className="block">
        <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
          Mention 别名 (逗号分隔)
        </span>
        <input
          className="mt-1 block w-full rounded border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
          value={form.mentionPatterns}
          onChange={(e) => setForm((f) => ({ ...f, mentionPatterns: e.target.value }))}
          placeholder="@tabby, 虎斑, tabby"
        />
      </label>
      <div className="flex justify-end gap-2">
        <button
          onClick={onCancel}
          className="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-200 dark:text-gray-400 dark:hover:bg-gray-700"
        >
          取消
        </button>
        <button
          onClick={() => {
            const mentions = form.mentionPatterns
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean);
            onSave({
              ...form,
              name: form.name || form.id,
              displayName: form.displayName || form.name,
              mentionPatterns: mentions,
            });
          }}
          className="flex items-center gap-1 rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700"
        >
          <Save size={14} />
          {isEdit ? "保存" : "创建"}
        </button>
      </div>
    </div>
  );
}

export function CatSettings() {
  const cats = useCatStore((s) => s.cats);
  const loading = useCatStore((s) => s.loading);
  const fetchCats = useCatStore((s) => s.fetchCats);
  const createCat = useCatStore((s) => s.createCat);
  const updateCat = useCatStore((s) => s.updateCat);
  const deleteCat = useCatStore((s) => s.deleteCat);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCats();
  }, []);

  if (loading && cats.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-600 dark:text-gray-400">
          管理可用的 AI 助手（猫咪）。点击编辑按钮修改配置。
        </div>
        <button
          onClick={() => {
            setShowCreate(true);
            setEditingId(null);
          }}
          className="flex items-center gap-1 rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700"
        >
          <Plus size={14} />
          添加猫咪
        </button>
      </div>

      {error && (
        <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">
            关闭
          </button>
        </div>
      )}

      <div className="grid gap-3">
        {showCreate && (
          <CatEditor
            onSave={async (data) => {
              try {
                setError(null);
                await createCat({
                  id: data.id!,
                  name: data.name,
                  displayName: data.displayName,
                  provider: data.provider,
                  defaultModel: data.defaultModel || undefined,
                  personality: data.personality || undefined,
                  mentionPatterns: data.mentionPatterns,
                });
                setShowCreate(false);
              } catch (e: any) {
                setError(e.message);
              }
            }}
            onCancel={() => setShowCreate(false)}
          />
        )}

        {cats.map((cat) =>
          editingId === cat.id ? (
            <CatEditor
              key={cat.id}
              cat={cat}
              onSave={async (data) => {
                try {
                  setError(null);
                  await updateCat(cat.id, {
                    name: data.name,
                    displayName: data.displayName,
                    provider: data.provider,
                    defaultModel: data.defaultModel || undefined,
                    personality: data.personality || undefined,
                    mentionPatterns: data.mentionPatterns,
                  });
                  setEditingId(null);
                } catch (e: any) {
                  setError(e.message);
                }
              }}
              onCancel={() => setEditingId(null)}
            />
          ) : (
            <div
              key={cat.id}
              className="flex items-start gap-4 rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
            >
              <div className="text-3xl">{cat.avatar || "🐱"}</div>

              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h4 className="font-medium text-gray-900 dark:text-gray-100">
                    {cat.displayName || cat.name}
                  </h4>
                  <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-500 dark:bg-gray-700 dark:text-gray-400">
                    {cat.id}
                  </span>
                  {cat.isAvailable ? (
                    <span className="flex items-center gap-0.5 rounded bg-green-100 px-1.5 py-0.5 text-xs text-green-700 dark:bg-green-900/30 dark:text-green-400">
                      <Check size={10} />
                      可用
                    </span>
                  ) : (
                    <span className="flex items-center gap-0.5 rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600 dark:bg-gray-700 dark:text-gray-400">
                      <X size={10} />
                      不可用
                    </span>
                  )}
                </div>

                <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                  {cat.provider}
                  {cat.defaultModel ? ` / ${cat.defaultModel}` : ""}
                </p>

                {cat.personality && (
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400 line-clamp-2">
                    {cat.personality}
                  </p>
                )}

                {cat.mentionPatterns && cat.mentionPatterns.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {cat.mentionPatterns.map((m) => (
                      <span
                        key={m}
                        className="rounded bg-purple-50 px-1.5 py-0.5 text-xs text-purple-600 dark:bg-purple-900/30 dark:text-purple-400"
                      >
                        {m}
                      </span>
                    ))}
                  </div>
                )}

                {cat.roles && cat.roles.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {cat.roles.map((role) => (
                      <span
                        key={role}
                        className="rounded bg-blue-50 px-2 py-0.5 text-xs text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"
                      >
                        {role}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div className="flex gap-1">
                <button
                  onClick={() => {
                    setEditingId(cat.id);
                    setShowCreate(false);
                  }}
                  className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-blue-600 dark:hover:bg-gray-700"
                  title="编辑"
                >
                  <Pencil size={14} />
                </button>
                <button
                  onClick={async () => {
                    if (confirm(`确定删除猫咪 "${cat.displayName || cat.name}"？`)) {
                      try {
                        setError(null);
                        await deleteCat(cat.id);
                      } catch (e: any) {
                        setError(e.message);
                      }
                    }
                  }}
                  className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-red-600 dark:hover:bg-gray-700"
                  title="删除"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          )
        )}

        {cats.length === 0 && !showCreate && (
          <div className="py-12 text-center text-gray-500 dark:text-gray-400">
            暂无配置猫咪，点击上方"添加猫咪"按钮创建
          </div>
        )}
      </div>
    </div>
  );
}
