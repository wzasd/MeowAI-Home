/** Signal inbox — article aggregation page with real API integration. */

import { useState, useEffect, useCallback } from "react";
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
  Loader2,
  AlertCircle,
  CheckCircle,
  Save,
  MessageSquare,
} from "lucide-react";
import {
  useSignals,
  type SignalArticle,
  type SignalSource,
  type ArticleStatus,
  type ArticleTier,
} from "../../hooks/useSignals";

const TIER_COLORS: Record<ArticleTier, string> = {
  S: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  A: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  B: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  C: "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400",
};

const STATUS_LABELS: Record<string, string> = {
  all: "全部",
  unread: "未读",
  reading: "阅读中",
  read: "已读",
  starred: "收藏",
};

function TierBadge({ tier }: { tier: ArticleTier }) {
  return <span className={`rounded px-1.5 py-0.5 text-[10px] font-bold ${TIER_COLORS[tier]}`}>{tier}</span>;
}

function ArticleList({
  articles,
  selectedId,
  onSelect,
  loading,
}: {
  articles: SignalArticle[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  loading: boolean;
}) {
  if (loading) {
    return (
      <div className="flex h-40 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    );
  }

  if (articles.length === 0) {
    return (
      <div className="flex h-40 flex-col items-center justify-center text-gray-400">
        <AlertCircle size={24} className="mb-2" />
        <p className="text-sm">暂无文章</p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {articles.map((article) => (
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
            <div className="min-w-0 flex-1">
              <h4 className="truncate text-sm font-medium text-gray-800 dark:text-gray-200">{article.title}</h4>
              <p className="mt-0.5 line-clamp-2 text-xs text-gray-500 dark:text-gray-400">{article.summary}</p>
              <div className="mt-1 flex items-center gap-2 text-[10px] text-gray-400">
                <span>{article.source}</span>
                <span>{article.publishedAt?.slice(5, 10) || "—"}</span>
                {article.readTime && <span>{article.readTime}分钟</span>}
              </div>
            </div>
            {article.status === "starred" && <Star size={14} className="shrink-0 text-amber-500" fill="currentColor" />}
          </div>
        </button>
      ))}
    </div>
  );
}

function ArticleDetail({
  article,
  onStatusChange,
  onStar,
  getNotes,
  saveNotes,
  generatePodcast,
  generateResearch,
}: {
  article: SignalArticle;
  onStatusChange: (id: string, status: ArticleStatus) => Promise<boolean>;
  onStar: (id: string) => Promise<boolean>;
  getNotes: (id: string) => Promise<string>;
  saveNotes: (id: string, notes: string) => Promise<boolean>;
  generatePodcast: (id: string) => Promise<Blob>;
  generateResearch: (id: string) => Promise<{ summary: string }>;
}) {
  const [studyMode, setStudyMode] = useState(false);
  const [notes, setNotes] = useState("");
  const [isMarkingRead, setIsMarkingRead] = useState(false);
  const [isStarring, setIsStarring] = useState(false);
  const [isSavingNotes, setIsSavingNotes] = useState(false);
  const [isGeneratingPodcast, setIsGeneratingPodcast] = useState(false);
  const [isGeneratingResearch, setIsGeneratingResearch] = useState(false);
  const [podcastUrl, setPodcastUrl] = useState<string | null>(null);
  const [researchReport, setResearchReport] = useState<string | null>(null);

  // Load notes when article changes or study mode opens
  useEffect(() => {
    if (studyMode) {
      getNotes(article.id).then(setNotes);
    }
  }, [article.id, studyMode, getNotes]);

  // Revoke podcast URL on unmount / article change
  useEffect(() => {
    return () => {
      if (podcastUrl) {
        URL.revokeObjectURL(podcastUrl);
      }
    };
  }, [article.id, podcastUrl]);

  const handleMarkRead = async () => {
    setIsMarkingRead(true);
    await onStatusChange(article.id, "read");
    setIsMarkingRead(false);
  };

  const handleStar = async () => {
    setIsStarring(true);
    await onStar(article.id);
    setIsStarring(false);
  };

  const handleSaveNotes = async () => {
    setIsSavingNotes(true);
    await saveNotes(article.id, notes);
    setIsSavingNotes(false);
  };

  const handleGeneratePodcast = async () => {
    setIsGeneratingPodcast(true);
    try {
      const blob = await generatePodcast(article.id);
      if (podcastUrl) URL.revokeObjectURL(podcastUrl);
      const url = URL.createObjectURL(blob);
      setPodcastUrl(url);
    } catch (e) {
      console.error("Podcast generation failed:", e);
    } finally {
      setIsGeneratingPodcast(false);
    }
  };

  const handleGenerateResearch = async () => {
    setIsGeneratingResearch(true);
    try {
      const report = await generateResearch(article.id);
      setResearchReport(report.summary);
    } catch (e) {
      console.error("Research generation failed:", e);
    } finally {
      setIsGeneratingResearch(false);
    }
  };

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
            <span className="flex items-center gap-1">
              <Clock size={12} /> {article.publishedAt?.slice(0, 10) || "—"}
            </span>
            {article.readTime && <span>{article.readTime}分钟阅读</span>}
          </div>
        </div>
        <div className="flex gap-1">
          <button
            onClick={handleStar}
            disabled={isStarring || article.status === "starred"}
            className={`rounded p-1.5 transition-colors ${
              article.status === "starred"
                ? "bg-amber-100 text-amber-500"
                : "text-gray-400 hover:bg-gray-100 hover:text-amber-500 dark:hover:bg-gray-700"
            }`}
            title="收藏"
          >
            {isStarring ? <Loader2 size={16} className="animate-spin" /> : <Star size={16} fill={article.status === "starred" ? "currentColor" : "none"} />}
          </button>
          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-blue-500 dark:hover:bg-gray-700"
            title="打开链接"
          >
            <ExternalLink size={16} />
          </a>
        </div>
      </div>

      {article.status === "unread" && (
        <div className="flex items-center gap-2 rounded-lg bg-blue-50 px-3 py-2 dark:bg-blue-900/20">
          <AlertCircle size={14} className="text-blue-500" />
          <span className="text-xs text-blue-700 dark:text-blue-400">未读文章</span>
          <button
            onClick={handleMarkRead}
            disabled={isMarkingRead}
            className="ml-auto flex items-center gap-1 rounded bg-blue-600 px-2 py-1 text-xs text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {isMarkingRead ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle size={12} />}
            标记已读
          </button>
        </div>
      )}

      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-gray-700 dark:bg-gray-800/50">
        <p className="text-sm leading-relaxed text-gray-700 dark:text-gray-300">{article.summary}</p>
      </div>

      <div className="flex flex-wrap gap-1">
        {article.keywords?.map((kw) => (
          <span
            key={kw}
            className="flex items-center gap-0.5 rounded bg-purple-50 px-2 py-0.5 text-xs text-purple-600 dark:bg-purple-900/30 dark:text-purple-400"
          >
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
          <div className="mt-3 space-y-3">
            {/* Notes */}
            <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 dark:border-blue-800 dark:bg-blue-900/20">
              <div className="flex items-center justify-between">
                <h5 className="text-xs font-semibold text-blue-700 dark:text-blue-400">学习笔记</h5>
                <button
                  onClick={handleSaveNotes}
                  disabled={isSavingNotes}
                  className="flex items-center gap-1 rounded bg-blue-600 px-2 py-1 text-[10px] text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {isSavingNotes ? <Loader2 size={10} className="animate-spin" /> : <Save size={10} />}
                  保存
                </button>
              </div>
              <textarea
                className="mt-2 w-full rounded border border-blue-200 bg-white p-2 text-sm dark:border-blue-700 dark:bg-gray-800 dark:text-white"
                rows={4}
                placeholder="记录你的学习心得..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>

            {/* Actions */}
            <div className="flex flex-wrap gap-2">
              <button
                onClick={handleGeneratePodcast}
                disabled={isGeneratingPodcast}
                className="flex items-center gap-1 rounded bg-green-600 px-3 py-1.5 text-xs text-white hover:bg-green-700 disabled:opacity-50"
              >
                {isGeneratingPodcast ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
                生成播客
              </button>
              <button
                onClick={handleGenerateResearch}
                disabled={isGeneratingResearch}
                className="flex items-center gap-1 rounded bg-blue-600 px-3 py-1.5 text-xs text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {isGeneratingResearch ? <Loader2 size={12} className="animate-spin" /> : <MessageSquare size={12} />}
                讨论（多猫研报）
              </button>
            </div>

            {/* Podcast player */}
            {podcastUrl && (
              <div className="rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
                <p className="mb-2 text-xs font-medium text-gray-600 dark:text-gray-400">播客预览</p>
                <audio src={podcastUrl} controls className="w-full" />
              </div>
            )}

            {/* Research report */}
            {researchReport && (
              <div className="rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800">
                <p className="mb-2 text-xs font-medium text-gray-600 dark:text-gray-400">多猫研究报告</p>
                <div className="max-h-64 overflow-y-auto whitespace-pre-wrap text-sm text-gray-700 dark:text-gray-300">
                  {researchReport}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function SourcesView({
  sources,
  onRefresh,
}: {
  sources: SignalSource[];
  onRefresh: (sourceId: string) => Promise<boolean>;
}) {
  const [refreshingId, setRefreshingId] = useState<string | null>(null);

  const handleRefresh = async (sourceId: string) => {
    setRefreshingId(sourceId);
    await onRefresh(sourceId);
    setRefreshingId(null);
  };

  if (sources.length === 0) {
    return (
      <div className="flex h-40 flex-col items-center justify-center text-gray-400">
        <AlertCircle size={24} className="mb-2" />
        <p className="text-sm">暂无来源配置</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {sources.map((source) => (
        <div
          key={source.id}
          className="flex items-center gap-3 rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-700 dark:bg-gray-800"
        >
          <div className={`h-3 w-3 rounded-full ${source.enabled ? "bg-green-500" : "bg-gray-400"}`} />
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-800 dark:text-gray-200">{source.name}</span>
              <TierBadge tier={source.tier} />
            </div>
            <div className="mt-0.5 flex items-center gap-2 text-[10px] text-gray-400">
              <span>{source.fetchMethod}</span>
              <span>{source.schedule}</span>
              {source.lastFetchedAt && <span>更新于 {source.lastFetchedAt.slice(5, 16)}</span>}
            </div>
          </div>
          <button
            onClick={() => handleRefresh(source.id)}
            disabled={refreshingId === source.id || !source.enabled}
            className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-blue-500 disabled:opacity-50 dark:hover:bg-gray-700"
            title="刷新"
          >
            {refreshingId === source.id ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
          </button>
        </div>
      ))}
    </div>
  );
}

export function SignalInboxPage() {
  const {
    articles,
    sources,
    loading,
    error,
    filter,
    setFilter,
    searchQuery,
    setSearchQuery,
    fetchArticles,
    fetchSources,
    searchArticles,
    updateArticleStatus,
    starArticle,
    refreshSource,
    getNotes,
    saveNotes,
    generatePodcast,
    generateResearch,
  } = useSignals();

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [tab, setTab] = useState<"inbox" | "sources">("inbox");
  const [isRefreshing, setIsRefreshing] = useState(false);

  const selectedArticle = articles.find((a) => a.id === selectedId);

  // Select first article when articles load
  useEffect(() => {
    if (articles.length > 0 && !selectedId) {
      setSelectedId(articles[0]!.id);
    }
  }, [articles, selectedId]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await fetchArticles();
    await fetchSources();
    setIsRefreshing(false);
  };

  const handleSearch = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      await searchArticles(searchQuery);
    },
    [searchArticles, searchQuery]
  );

  const handleSelect = (id: string) => {
    setSelectedId(id);
    const article = articles.find((a) => a.id === id);
    if (article && article.status === "unread") {
      // Auto-mark as reading when selected
      updateArticleStatus(id, "reading");
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white px-4 py-3 dark:border-gray-700 dark:bg-gray-800">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">Signal 收件箱</h2>
          <div className="flex items-center gap-2">
            <button
              onClick={handleRefresh}
              disabled={isRefreshing || loading}
              className="flex items-center gap-1 rounded bg-blue-600 px-3 py-1.5 text-xs text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {isRefreshing ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
              刷新
            </button>
          </div>
        </div>
        {/* Tabs */}
        <div className="mt-2 flex gap-1">
          <button
            onClick={() => setTab("inbox")}
            className={`rounded px-3 py-1 text-xs font-medium ${
              tab === "inbox"
                ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                : "text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
            }`}
          >
            收件箱
          </button>
          <button
            onClick={() => setTab("sources")}
            className={`rounded px-3 py-1 text-xs font-medium ${
              tab === "sources"
                ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                : "text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
            }`}
          >
            来源管理
          </button>
        </div>
      </div>

      {error && (
        <div className="mx-4 mt-2 flex items-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600 dark:bg-red-900/20 dark:text-red-400">
          <AlertCircle size={14} />
          {error}
        </div>
      )}

      {tab === "sources" ? (
        <div className="flex-1 overflow-y-auto p-4">
          <SourcesView sources={sources} onRefresh={refreshSource} />
        </div>
      ) : (
        <div className="flex flex-1 overflow-hidden">
          {/* Left: article list */}
          <div className="flex w-80 shrink-0 flex-col border-r border-gray-200 dark:border-gray-700">
            {/* Filters */}
            <div className="border-b border-gray-200 p-2 dark:border-gray-700">
              <form onSubmit={handleSearch} className="flex items-center gap-1">
                <div className="relative flex-1">
                  <Search size={14} className="absolute left-2 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    className="w-full rounded border border-gray-200 bg-white py-1 pl-7 pr-2 text-xs dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                    placeholder="搜索文章..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>
              </form>
              <div className="mt-1.5 flex flex-wrap gap-1">
                {(["all", "unread", "starred", "read"] as const).map((f) => (
                  <button
                    key={f}
                    onClick={() => setFilter(f)}
                    className={`rounded px-2 py-0.5 text-[10px] font-medium ${
                      filter === f
                        ? "bg-gray-200 text-gray-800 dark:bg-gray-600 dark:text-gray-200"
                        : "text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
                    }`}
                  >
                    {STATUS_LABELS[f]}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-2">
              <ArticleList articles={articles} selectedId={selectedId} onSelect={handleSelect} loading={loading} />
            </div>
          </div>

          {/* Right: detail */}
          <div className="flex-1 overflow-y-auto p-4">
            {selectedArticle ? (
              <ArticleDetail
                article={selectedArticle}
                onStatusChange={updateArticleStatus}
                onStar={starArticle}
                getNotes={getNotes}
                saveNotes={saveNotes}
                generatePodcast={generatePodcast}
                generateResearch={generateResearch}
              />
            ) : (
              <div className="flex h-full items-center justify-center text-gray-400">
                {loading ? <Loader2 className="h-6 w-6 animate-spin" /> : "选择一篇文章查看详情"}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
