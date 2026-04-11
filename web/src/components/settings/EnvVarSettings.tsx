import { useState, useEffect } from "react";
import { api } from "../../api/client";
import { Eye, EyeOff, Save, Loader2 } from "lucide-react";

interface EnvVar {
  name: string;
  category: string;
  description: string;
  default: string | null;
  current: string;
  isSet: boolean;
  required: boolean;
  sensitive: boolean;
  allowedValues: string[] | null;
}

export function EnvVarSettings() {
  const [vars, setVars] = useState<EnvVar[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [showSecret, setShowSecret] = useState<Record<string, boolean>>({});
  const [editedValues, setEditedValues] = useState<Record<string, string>>({});

  useEffect(() => {
    fetchEnvVars();
  }, []);

  const fetchEnvVars = async () => {
    try {
      const data = await api.config.listEnvVars();
      setVars(data.variables);
      setCategories(data.categories);
    } catch (error) {
      console.error("Failed to fetch env vars:", error);
    } finally {
      setLoading(false);
    }
  };

  const saveVar = async (name: string) => {
    setSaving(name);
    try {
      const value = editedValues[name];
      if (value === undefined) return;
      await api.config.updateEnvVar(name, value);
      await fetchEnvVars();
      setEditedValues((prev) => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
    } catch (error) {
      console.error("Failed to save env var:", error);
    } finally {
      setSaving(null);
    }
  };

  const getCategoryLabel = (cat: string) => {
    const labels: Record<string, string> = {
      core: "核心",
      security: "安全",
      database: "数据库",
      ai: "AI 提供商",
      connector: "连接器",
    };
    return labels[cat] || cat;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  const varsByCategory = categories.reduce((acc, cat) => {
    acc[cat] = vars.filter((v) => v.category === cat);
    return acc;
  }, {} as Record<string, EnvVar[]>);

  return (
    <div className="space-y-8">
      <div className="text-sm text-gray-600 dark:text-gray-400">
        管理 MeowAI 的环境变量配置。注意：这些更改仅在当前运行时生效。
      </div>

      {categories.map((category) => (
        <div key={category}>
          <h4 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
            {getCategoryLabel(category)}
          </h4>

          <div className="space-y-3">
            {varsByCategory[category]?.map((envVar) => (
              <div
                key={envVar.name}
                className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-700 dark:bg-gray-800"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <code className="rounded bg-gray-100 px-2 py-0.5 text-sm font-mono text-gray-800 dark:bg-gray-700 dark:text-gray-200">
                        {envVar.name}
                      </code>
                      {envVar.required && (
                        <span className="rounded bg-red-100 px-1.5 py-0.5 text-xs text-red-700 dark:bg-red-900/30 dark:text-red-400">
                          必需
                        </span>
                      )}
                      {envVar.isSet && (
                        <span className="rounded bg-green-100 px-1.5 py-0.5 text-xs text-green-700 dark:bg-green-900/30 dark:text-green-400">
                          已设置
                        </span>
                      )}
                    </div>

                    <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                      {envVar.description}
                    </p>

                    {envVar.default && (
                      <p className="mt-1 text-xs text-gray-500">
                        默认值: {envVar.default}
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    {envVar.sensitive && (
                      <button
                        onClick={() =>
                          setShowSecret((prev) => ({
                            ...prev,
                            [envVar.name]: !prev[envVar.name],
                          }))
                        }
                        className="rounded p-1 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700"
                      >
                        {showSecret[envVar.name] ? (
                          <EyeOff size={16} />
                        ) : (
                          <Eye size={16} />
                        )}
                      </button>
                    )}
                  </div>
                </div>

                <div className="mt-3 flex gap-2">
                  {envVar.allowedValues ? (
                    <select
                      value={editedValues[envVar.name] ?? envVar.current}
                      onChange={(e) =>
                        setEditedValues((prev) => ({
                          ...prev,
                          [envVar.name]: e.target.value,
                        }))
                      }
                      className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
                    >
                      {envVar.allowedValues.map((val) => (
                        <option key={val} value={val}>
                          {val}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      type={
                        envVar.sensitive && !showSecret[envVar.name]
                          ? "password"
                          : "text"
                      }
                      value={editedValues[envVar.name] ?? envVar.current}
                      onChange={(e) =>
                        setEditedValues((prev) => ({
                          ...prev,
                          [envVar.name]: e.target.value,
                        }))
                      }
                      placeholder={envVar.default || ""}
                      className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
                    />
                  )}

                  <button
                    onClick={() => saveVar(envVar.name)}
                    disabled={
                      saving === envVar.name ||
                      editedValues[envVar.name] === undefined
                    }
                    className="flex items-center gap-1 rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    {saving === envVar.name ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      <Save size={14} />
                    )}
                    保存
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
