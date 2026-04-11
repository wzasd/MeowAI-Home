/** Signal inbox — article aggregation page. */

import { useState } from "react";
import {
  Star,
  ExternalLink,
  Clock,
  Tag,
  ChevronDown,
  ChevronRight,
  Search,
  RefreshCw,
  BookMarked,
  Play,
} from "lucide-react";

// === Types ===

type ArticleTier = "S" | "A" | "B" | "C";
type ArticleStatus = "unread" | "reading" | "read" | "starred";

interface SignalArticle {
  id: string;
  title: string;
  url: string;
  source: string;
  tier: ArticleTier;
  status: ArticleStatus;
  summary: string;
  keywords: string[];
  publishedAt: string;
  readTime?: number;
}

interface SignalSource {
  id: string;
  name: string;
  tier: ArticleTier;
  fetchMethod: string;
  schedule: string;
  lastFetchedAt?: string;
  enabled: boolean;
}

// === Mock data ===

const MOCK_ARTICLES: SignalArticle[] = [
  {
    id: "a1", title: "GPT-5 发布：多模态推理能力大幅提升",
    url: "https://example.com/gpt5", source: "OpenAI Blog", tier: "S",
    status: "unread", summary: "OpenAI 发布 GPT-5，在多模态推理、长文本理解和代码生成方面取得重大突破...",
    keywords: ["GPT-5", "多模态", "LLM"], publishedAt: "2026-04-11T08:00:00Z", readTime: 5,
  },
  {
    id: "a2", title: "Claude 4.5 架构解析：MoE 与长上下文",
    url: "https://example.com/claude", source: "Anthropic Blog", tier: "S",
    status: "starred", summary: "Anthropic 发布 Claude 4.5 技术报告，详细介绍了 MoE 架构设计...",
    keywords: ["Claude", "MoE", "架构"], publishedAt: "2026-04-10T14:00:00Z", readTime: 8,
  },
  {
    id: "a3", title: "React 20 发布：Server Components 成为默认",
    url: "https://example.com/react20", source: "React Blog", tier: "A",
    status: "unread", summary: "React 20 正式发布，Server Components 成为默认渲染模式...",
    keywords: ["React", "RSC", "前端"], publishedAt: "2026-04-10T10:00:00Z", readTime: 4,
  },
  {
    id: "a4", title: "Rust 在 AI 推理引擎中的应用趋势",
    url: "https://example.com/rust-ai", source: "Hacker News", tier: "B",
    status: "read", summary: "越来越多的 AI 推理引擎开始采用 Rust 编写核心计算模块...",
    keywords: ["Rust", "AI推理", "性能"], publishedAt: "2026-04-09T16:00:00Z", readTime: 3,
  },
  {
    id: "a5", title: "Agent 框架对比：LangGraph vs CrewAI vs AutoGen",
    url: "https://example.com/agents", source: "TechCrunch", tier: "A",
    status: "unread", summary: "本文对比了三大 Agent 框架在多步骤任务编排、工具集成...",
    keywords: ["Agent", "LangGraph", "CrewAI"], publishedAt: "2026-04-09T09:00:00Z", readTime: 6,
  },
];

const MOCK_SOURCES: SignalSource[] = [
  { id: "s1", name: "OpenAI Blog", tier: "S", fetchMethod: "rss", schedule: "0 */4 * * *", enabled: true },
  { id: "s2", name: "Anthropic Blog", tier: "S", fetchMethod: "rss", schedule: "0 */4 * * *", enabled: true },
  { id: "s3", name: "Hacker News", tier: "A", fetchMethod: "json_api", schedule: "*/30 * * * *", enabled: true },
  { id: "s4", name: "TechCrunch AI", tier: "B", fetchMethod: "webpage", schedule: "0 */6 * * *", enabled: true },
  { id: "s5", name: "React Blog", tier: "A", fetchMethod: "rss", schedule: "0 */8 * * *", enabled: false },
];

const TIER_COLORS: Record<ArticleTier, string> = {
  S: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  A: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  B: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  C: "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400",
};

// === Sub-components ===

function TierBadge({ tier }: { tier: ArticleTier }) {
  return <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${TIER_COLORS[tier]}`}>{tier}</span>;
}

function ArticleList({
  articles, selectedId, onSelect, filter,
}: {
  articles: SignalArticle[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  filter: ArticleStatus | "all";
}) {
  const filtered = filter === "all" ? articles : articles.filter((a) => a.status === filter);
  return (
    <div className="space-y-1">
      {filtered.map((article) => (
        <button
          key={article.id}
          onClick={() => onSelect(article.id)}
          className={`w-full rounded-lg border p-3 text-left transition-colors ${
            selectedId === article.id
              ? "border-blue-300 bg-blue-50 dark:border-blue-700 dark:bg-blue-900/20"
              : "border-gray-200 bg-white hover:border-gray-300 dark:border-gray-700 dark:bg-gray-800 dark:hover:border-gray-600"
          }`}
        >
          <div className="flex items-start gap-2">
            <TierBadge tier={article.tier} />
            <div className="flex-1 min-w-0">
              <h4 className="truncate text-sm font-medium text-gray-800 dark:text-gray-200">{article.title}</h4>
              <p className="mt-0.5 line-clamp-2 text-xs text-gray-500 dark:text-gray-400">{article.summary}</p>
              <div className="mt-1 flex items-center gap-2 text-[10px] text-gray-400">
                <span>{article.source}</span>
                <span>{article.publishedAt.slice(5, 10)}</span>
                {article.readTime && <span>{article.readTime}分钟</span>}
              </div>
            </div>
            {article.status === "starred" && <Star size={14} className="shrink-0 text-amber-500" fill="currentColor" />}
          </div>
        </button>
      ))}
      {filtered.length === 0 && (
        <p className="py-8 text-center text-sm text-gray-400">暂无文章</p>
      )}
    </div>
  );
}

function ArticleDetail({ article }: { article: SignalArticle }) {
  const [studyMode, setStudyMode] = useState(false);

  return (
    <div className="space-y-4">
      <div className="flex items-start gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <TierBadge tier={article.tier} />
            <span className="text-xs text-gray-400">{article.source}</span>
          </div>
          <h2 className="mt-2 text-lg font-bold text-gray-900 dark:text-gray-100">{article.title}</h2>
          <div className="mt-1 flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
            <span className="flex items-center gap-1"><Clock size={12} /> {article.publishedAt.slice(0, 10)}</span>
            {article.readTime && <span>{article.readTime}分钟阅读</span>}
          </div>
        </div>
        <div className="flex gap-1">
          <button className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-amber-500 dark:hover:bg-gray-700" title="收藏">
            <Star size={16} />
          </button>
          <a href={article.url} target="_blank" className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-blue-500 dark:hover:bg-gray-700" title="打开链接">
            <ExternalLink size={16} />
          </a>
        </div>
      </div>

      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800/50">
        <p className="text-sm leading-relaxed text-gray-700 dark:text-gray-300">{article.summary}</p>
      </div>

      <div className="flex flex-wrap gap-1">
        {article.keywords.map((kw) => (
          <span key={kw} className="flex items-center gap-0.5 rounded bg-purple-50 px-2 py-0.5 text-xs text-purple-600 dark:bg-purple-900/30 dark:text-purple-400">
            <Tag size={10} /> {kw}
          </span>
        ))}
      </div>

      {/* Study mode */}
      <div className="border-t border-gray-200 pt-3 dark:border-gray-700">
        <button
          onClick={() => setStudyMode(!studyMode)}
          className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400"
        >
          {studyMode ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          <BookMarked size={14} />
          学习模式
        </button>
        {studyMode && (
          <div className="mt-3 space-y-2">
            <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 dark:border-blue-800 dark:bg-blue-900/20">
              <h5 className="text-xs font-semibold text-blue-700 dark:text-blue-400">学习笔记</h5>
              <textarea
                className="mt-2 w-full rounded border border-blue-200 bg-white p-2 text-sm dark:border-blue-700 dark:bg-gray-800 dark:text-white"
                rows={3}
                placeholder="记录你的学习心得..."
              />
            </div>
            <div className="flex gap-2">
              <button className="flex items-center gap-1 rounded bg-green-600 px-3 py-1.5 text-xs text-white hover:bg-green-700">
                <Play size={12} /> 生成播客
              </button>
              <button className="flex items-center gap-1 rounded bg-blue-600 px-3 py-1.5 text-xs text-white hover:bg-blue-700">
                讨论
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function SourcesView({ sources }: { sources: SignalSource[] }) {
  return (
    <div className="space-y-2">
      {sources.map((source) => (
        <div key={source.id} className="flex items-center gap-3 rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
          <div className={`h-3 w-3 rounded-full ${source.enabled ? "bg-green-500" : "bg-gray-400"}`} />
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-800 dark:text-gray-200">{source.name}</span>
              <TierBadge tier={source.tier} />
            </div>
            <div className="mt-0.5 flex items-center gap-2 text-[10px] text-gray-400">
              <span>{source.fetchMethod}</span>
              <span>{source.schedule}</span>
            </div>
          </div>
          <button className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-blue-500 dark:hover:bg-gray-700">
            <RefreshCw size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}

// === Main Component ===

export function SignalInboxPage() {
  const [articles] = useState<SignalArticle[]>(MOCK_ARTICLES);
  const [sources] = useState<SignalSource[]>(MOCK_SOURCES);
  const [selectedId, setSelectedId] = useState<string | null>("a1");
  const [filter, setFilter] = useState<ArticleStatus | "all">("all");
  const [tab, setTab] = useState<"inbox" | "sources">("inbox");
  const [searchQuery, setSearchQuery] = useState("");

  const selected = articles.find((a) => a.id === selectedId);

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-4 py-3 dark:border-gray-700 dark:bg-gray-800">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">Signal 收件箱</h2>
          <div className="flex items-center gap-2">
            <button className="flex items-center gap-1 rounded bg-blue-600 px-3 py-1.5 text-xs text-white hover:bg-blue-700">
              <RefreshCw size={12} /> 刷新
            </button>
          </div>
        </div>
        {/* Tabs */}
        <div className="mt-2 flex gap-1">
          <button
            onClick={() => setTab("inbox")}
            className={`rounded px-3 py-1 text-xs font-medium ${tab === "inbox" ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" : "text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"}`}
          >
            收件箱
          </button>
          <button
            onClick={() => setTab("sources")}
            className={`rounded px-3 py-1 text-xs font-medium ${tab === "sources" ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" : "text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"}`}
          >
            来源管理
          </button>
        </div>
      </div>

      {tab === "sources" ? (
        <div className="flex-1 overflow-y-auto p-4">
          <SourcesView sources={sources} />
        </div>
      ) : (
        <div className="flex flex-1 overflow-hidden">
          {/* Left: article list */}
          <div className="flex w-80 shrink-0 flex-col border-r border-gray-200 dark:border-gray-700">
            {/* Filters */}
            <div className="border-b border-gray-200 p-2 dark:border-gray-700">
              <div className="flex items-center gap-1">
                <div className="relative flex-1">
                  <Search size={14} className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    className="w-full rounded border border-gray-200 bg-white py-1 pl-7 pr-2 text-xs dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                    placeholder="搜索文章..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
              </div>
              <div className="mt-1.5 flex gap-1">
                {(["all", "unread", "starred", "read"] as const).map((f) => (
                  <button
                    key={f}
                    onClick={() => setFilter(f)}
                    className={`rounded px-2 py-0.5 text-[10px] font-medium ${
                      filter === f ? "bg-gray-200 text-gray-800 dark:bg-gray-600 dark:text-gray-200" : "text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
                    }`}
                  >
                    {f === "all" ? "全部" : f === "unread" ? "未读" : f === "starred" ? "收藏" : "已读"}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-2">
              <ArticleList articles={articles} selectedId={selectedId} onSelect={setSelectedId} filter={filter} />
            </div>
          </div>

          {/* Right: detail */}
          <div className="flex-1 overflow-y-auto p-4">
            {selected ? (
              <ArticleDetail article={selected} />
            ) : (
              <div className="flex h-full items-center justify-center text-gray-400">
                选择一篇文章查看详情
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
