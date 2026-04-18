import { useCallback, useEffect, useState } from "react";
import { api } from "../../api/client";
import { Eye, EyeOff, Loader2, RefreshCw, Save } from "lucide-react";
import type { EnvVarResponse } from "../../types";
import { SettingsSectionCard, SettingsSummaryGrid } from "./SettingsSectionCard";
import { buildEnvVarSummaryCards } from "./settingsSummaryModels";

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

export function EnvVarSettings() {
  const [vars, setVars] = useState<EnvVarResponse[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showSecret, setShowSecret] = useState<Record<string, boolean>>({});
  const [editedValues, setEditedValues] = useState<Record<string, string>>({});

  const fetchEnvVars = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.config.listEnvVars();
      setVars(data.variables);
      setCategories(data.categories);
    } catch (error) {
      setError(getErrorMessage(error, "加载环境变量失败"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchEnvVars();
  }, [fetchEnvVars]);

  const saveVar = async (name: string) => {
    const value = editedValues[name];
    if (value === undefined) return;

    setSaving(name);
    setError(null);
    try {
      await api.config.updateEnvVar(name, value);
      await fetchEnvVars();
      setEditedValues((prev) => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
    } catch (error) {
      setError(getErrorMessage(error, "保存环境变量失败"));
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

  const varsByCategory = categories.reduce(
    (acc, cat) => {
      acc[cat] = vars.filter((v) => v.category === cat);
      return acc;
    },
    {} as Record<string, EnvVarResponse[]>
  );
  const summaryCards = buildEnvVarSummaryCards(vars);
  const orderedCategories =
    categories.length > 0 ? categories : Array.from(new Set(vars.map((envVar) => envVar.category)));

  return (
    <div className="space-y-5">
      <SettingsSummaryGrid items={summaryCards} />

      <SettingsSectionCard
        eyebrow="Runtime Config"
        title="环境变量与运行时参数"
        description="这里保留显式保存契约。先判断哪些项必须补齐、哪些敏感值需要复核，再逐项提交到当前运行时。"
        actions={
          <button
            type="button"
            onClick={fetchEnvVars}
            className="inline-flex items-center gap-1 rounded-full border border-[var(--border)] bg-white/65 px-3 py-2 text-sm text-[var(--text-soft)] transition-colors hover:border-[var(--border-strong)] hover:text-[var(--text-strong)] dark:bg-white/[0.05]"
          >
            <RefreshCw size={14} />
            刷新变量
          </button>
        }
      >
        <div className="space-y-4">
          {error && (
            <div className="rounded-[1rem] border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-500 dark:border-red-900/40 dark:bg-red-900/20 dark:text-red-400">
              {error}
            </div>
          )}

          <div className="rounded-[1.2rem] border border-[var(--border)] bg-white/55 px-4 py-3 text-sm leading-7 text-[var(--text-soft)] dark:bg-white/[0.03]">
            修改只会作用于当前运行时。必需项缺失和敏感项会在上面的摘要卡里直接暴露出来，避免在长表单里埋没。
          </div>

          {orderedCategories.length === 0 ? (
            <div className="rounded-[1.25rem] border border-dashed border-[var(--border)] bg-white/45 px-5 py-10 text-center dark:bg-white/[0.03]">
              <p className="text-sm font-medium text-[var(--text-strong)]">
                当前没有可配置的环境变量
              </p>
              <p className="mt-2 text-sm leading-7 text-[var(--text-soft)]">
                如果这里应该有内容，先检查后端配置元数据是否已暴露到 `/api/config/env`。
              </p>
            </div>
          ) : (
            orderedCategories.map((category) => (
              <div
                key={category}
                className="rounded-[1.2rem] border border-[var(--border)] bg-white/55 p-4 dark:bg-white/[0.03]"
              >
                <div className="mb-4 flex items-center justify-between gap-3">
                  <div>
                    <h4 className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--text-faint)]">
                      {getCategoryLabel(category)}
                    </h4>
                    <p className="mt-1 text-sm text-[var(--text-soft)]">
                      {varsByCategory[category]?.length ?? 0} 个变量
                    </p>
                  </div>
                </div>

                <div className="space-y-3">
                  {varsByCategory[category]?.map((envVar) => {
                    const draftValue = editedValues[envVar.name];
                    const currentValue = draftValue ?? envVar.current;
                    const isDirty = draftValue !== undefined && draftValue !== envVar.current;

                    return (
                      <div
                        key={envVar.name}
                        className="rounded-[1.15rem] border border-[var(--border)] bg-white/80 p-4 shadow-[0_18px_40px_-28px_rgba(15,23,42,0.45)] dark:bg-white/[0.04]"
                      >
                        <div className="flex items-start justify-between gap-4">
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <code className="rounded-lg bg-gray-100 px-2 py-0.5 font-mono text-sm text-gray-800 dark:bg-gray-700 dark:text-gray-200">
                                {envVar.name}
                              </code>
                              {envVar.required && (
                                <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-700 dark:bg-red-900/30 dark:text-red-400">
                                  必需
                                </span>
                              )}
                              {envVar.isSet && (
                                <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700 dark:bg-green-900/30 dark:text-green-400">
                                  已设置
                                </span>
                              )}
                              {envVar.sensitive && (
                                <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                                  敏感
                                </span>
                              )}
                              {envVar.allowedValues && envVar.allowedValues.length > 0 && (
                                <span className="rounded-full bg-sky-100 px-2 py-0.5 text-xs text-sky-700 dark:bg-sky-900/30 dark:text-sky-400">
                                  枚举项
                                </span>
                              )}
                            </div>

                            <p className="mt-2 text-sm leading-7 text-[var(--text-soft)]">
                              {envVar.description}
                            </p>

                            <div className="mt-2 flex flex-wrap gap-3 text-xs text-[var(--text-faint)]">
                              {envVar.default && <span>默认值：{envVar.default}</span>}
                              {!envVar.isSet && <span>当前未设置，运行时会回落到默认逻辑</span>}
                            </div>
                          </div>

                          {envVar.sensitive && (
                            <button
                              type="button"
                              onClick={() =>
                                setShowSecret((prev) => ({
                                  ...prev,
                                  [envVar.name]: !prev[envVar.name],
                                }))
                              }
                              className="rounded-full border border-[var(--border)] p-2 text-[var(--text-faint)] transition-colors hover:border-[var(--border-strong)] hover:text-[var(--text-strong)]"
                            >
                              {showSecret[envVar.name] ? <EyeOff size={16} /> : <Eye size={16} />}
                            </button>
                          )}
                        </div>

                        <div className="mt-4 flex flex-col gap-2 lg:flex-row">
                          {envVar.allowedValues ? (
                            <select
                              value={currentValue}
                              onChange={(e) =>
                                setEditedValues((prev) => ({
                                  ...prev,
                                  [envVar.name]: e.target.value,
                                }))
                              }
                              className="flex-1 rounded-xl border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
                            >
                              {envVar.allowedValues.map((value) => (
                                <option key={value} value={value}>
                                  {value}
                                </option>
                              ))}
                            </select>
                          ) : (
                            <input
                              type={
                                envVar.sensitive && !showSecret[envVar.name] ? "password" : "text"
                              }
                              value={currentValue}
                              onChange={(e) =>
                                setEditedValues((prev) => ({
                                  ...prev,
                                  [envVar.name]: e.target.value,
                                }))
                              }
                              placeholder={envVar.default || ""}
                              className="flex-1 rounded-xl border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200"
                            />
                          )}

                          <button
                            type="button"
                            onClick={() => saveVar(envVar.name)}
                            disabled={saving === envVar.name || !isDirty}
                            className="inline-flex items-center justify-center gap-1 rounded-xl bg-[var(--accent)] px-4 py-2 text-sm font-medium text-[var(--accent-contrast)] transition-opacity hover:opacity-90 disabled:opacity-50"
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
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </div>
      </SettingsSectionCard>
    </div>
  );
}
