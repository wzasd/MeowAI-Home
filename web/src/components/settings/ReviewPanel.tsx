/** Review panel — manage pending PR reviews and CI status. */

import { useState } from "react";
import {
  GitPullRequest,
  CheckCircle2,
  XCircle,
  Loader2,
  Trash2,
  UserPlus,
  RefreshCw,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Plus,
  X,
} from "lucide-react";
import { useReview, type ReviewTracking, type PRCIState } from "../../hooks/useReview";

function statusBadge(status: string) {
  const map: Record<string, string> = {
    pending: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    approved: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    changes_requested: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    commented: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    merged: "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400",
    closed: "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400",
    success: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
    failure: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    error: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  };
  return (
    <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${map[status] || map.pending}`}>
      {status}
    </span>
  );
}

function ReviewRow({
  review,
  onAssign,
  onDelete,
}: {
  review: ReviewTracking;
  onAssign: (repo: string, pr: number) => void;
  onDelete: (repo: string, pr: number) => void;
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-gray-200 bg-white px-3 py-2 dark:border-gray-700 dark:bg-gray-800">
      <GitPullRequest size={16} className="text-blue-500" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 truncate">
          <span className="text-sm font-medium text-gray-800 dark:text-gray-200">
            #{review.pr_number} {review.pr_title}
          </span>
          {statusBadge(review.status)}
        </div>
        <div className="text-[10px] text-gray-500 dark:text-gray-400">
          {review.repository} · 审阅 {review.review_count} · 评论 {review.comments_count}
          {review.assigned_cat_id && <span className="ml-2 text-blue-600">@{review.assigned_cat_id}</span>}
        </div>
      </div>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onAssign(review.repository, review.pr_number)}
          className="rounded p-1 text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20"
          title="分配审阅者"
        >
          <UserPlus size={14} />
        </button>
        <button
          onClick={() => onDelete(review.repository, review.pr_number)}
          className="rounded p-1 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
          title="删除跟踪"
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  );
}

function CIPRRow({ pr }: { pr: PRCIState }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-800">
      <div className="flex items-center gap-3 px-3 py-2">
        {pr.overall_status === "success" ? (
          <CheckCircle2 size={16} className="text-green-500" />
        ) : pr.overall_status === "failure" || pr.overall_status === "error" ? (
          <XCircle size={16} className="text-red-500" />
        ) : (
          <Loader2 size={16} className="animate-spin text-amber-500" />
        )}
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-800 dark:text-gray-200">
              #{pr.pr_number} {pr.repository}
            </span>
            {statusBadge(pr.overall_status)}
          </div>
          <div className="text-[10px] text-gray-500 dark:text-gray-400">
            {pr.checks.length} 个检查 · 更新于 {new Date(pr.updated_at * 1000).toLocaleString()}
          </div>
        </div>
        <button
          onClick={() => setExpanded((v) => !v)}
          className="rounded p-1 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
        >
          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
      </div>
      {expanded && (
        <div className="border-t border-gray-100 px-3 py-2 dark:border-gray-700">
          {pr.checks.length === 0 ? (
            <div className="text-[10px] text-gray-400">暂无检查详情</div>
          ) : (
            <div className="space-y-1">
              {pr.checks.map((c, i) => (
                <div key={i} className="flex items-center gap-2 text-[10px]">
                  <span
                    className={
                      c.status === "success"
                        ? "text-green-500"
                        : c.status === "failure" || c.status === "error"
                        ? "text-red-500"
                        : "text-amber-500"
                    }
                  >
                    {c.status}
                  </span>
                  <span className="text-gray-700 dark:text-gray-300">{c.name}</span>
                  {c.url && (
                    <a
                      href={c.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-blue-600 hover:underline"
                    >
                      查看
                    </a>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function AssignModal({
  isOpen,
  onClose,
  repo,
  pr,
  onAssign,
}: {
  isOpen: boolean;
  onClose: () => void;
  repo: string;
  pr: number;
  onAssign: (catId: string) => void;
}) {
  const [catId, setCatId] = useState("orange");
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-sm rounded-lg bg-white p-4 dark:bg-gray-800">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100">
            分配审阅者 #{pr}
          </h3>
          <button onClick={onClose} className="rounded p-1 text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700">
            <X size={16} />
          </button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">Cat ID</label>
            <input
              type="text"
              value={catId}
              onChange={(e) => setCatId(e.target.value)}
              className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            />
          </div>
          <div className="flex justify-end gap-2">
            <button
              onClick={onClose}
              className="rounded bg-gray-200 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
            >
              取消
            </button>
            <button
              onClick={() => {
                onAssign(catId);
                onClose();
              }}
              className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700"
            >
              分配
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export function ReviewPanel() {
  const {
    pending,
    ciPRs,
    loading,
    error,
    fetchPending,
    fetchCIStatus,
    assignReviewer,
    deleteTracking,
    pollCI,
  } = useReview();

  const [assignOpen, setAssignOpen] = useState(false);
  const [assignTarget, setAssignTarget] = useState<{ repo: string; pr: number } | null>(null);

  const handleAssignClick = (repo: string, pr: number) => {
    setAssignTarget({ repo, pr });
    setAssignOpen(true);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-600 dark:text-gray-400">
          管理 GitHub PR 审阅与 CI 状态
          <span className="ml-2 rounded bg-gray-100 px-1.5 py-0.5 text-[10px] text-gray-600 dark:bg-gray-700 dark:text-gray-300">
            {pending.length} 待审
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={async () => {
              await fetchPending();
              await fetchCIStatus();
            }}
            className="flex items-center gap-1 rounded bg-gray-100 px-2 py-1 text-xs text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
          >
            <RefreshCw size={12} /> 刷新
          </button>
          <button
            onClick={async () => {
              await pollCI();
            }}
            className="flex items-center gap-1 rounded bg-blue-100 px-2 py-1 text-xs text-blue-700 hover:bg-blue-200 dark:bg-blue-900/30 dark:text-blue-400"
          >
            <RefreshCw size={12} /> 轮询 CI
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-1 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-600 dark:bg-red-900/20 dark:text-red-400">
          <AlertCircle size={12} />
          {error}
        </div>
      )}

      {/* Pending reviews */}
      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">
          待审 PR
        </h4>
        {loading && pending.length === 0 ? (
          <div className="py-8 text-center">
            <Loader2 size={24} className="animate-spin text-gray-400" />
          </div>
        ) : pending.length === 0 ? (
          <div className="rounded-lg border border-dashed border-gray-200 p-6 text-center text-sm text-gray-400 dark:border-gray-700">
            暂无待审 PR
          </div>
        ) : (
          <div className="space-y-2">
            {pending.map((review) => (
              <ReviewRow
                key={`${review.repository}#${review.pr_number}`}
                review={review}
                onAssign={handleAssignClick}
                onDelete={async (repo, pr) => {
                  await deleteTracking(repo, pr);
                }}
              />
            ))}
          </div>
        )}
      </div>

      {/* CI status */}
      <div>
        <h4 className="mb-2 text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">
          CI 状态
        </h4>
        {ciPRs.length === 0 ? (
          <div className="rounded-lg border border-dashed border-gray-200 p-6 text-center text-sm text-gray-400 dark:border-gray-700">
            暂无跟踪的 PR CI 状态
          </div>
        ) : (
          <div className="space-y-2">
            {ciPRs.map((pr) => (
              <CIPRRow key={`${pr.repository}#${pr.pr_number}`} pr={pr} />
            ))}
          </div>
        )}
      </div>

      {assignTarget && (
        <AssignModal
          isOpen={assignOpen}
          onClose={() => setAssignOpen(false)}
          repo={assignTarget.repo}
          pr={assignTarget.pr}
          onAssign={async (catId) => {
            await assignReviewer(assignTarget.repo, assignTarget.pr, catId);
          }}
        />
      )}
    </div>
  );
}
