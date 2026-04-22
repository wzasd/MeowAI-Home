/** Markdown content renderer with syntax highlighting and GFM support */

import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";

interface MarkdownContentProps {
  content: string;
  className?: string;
}

export function MarkdownContent({ content, className }: MarkdownContentProps) {
  return (
    <div className={`prose prose-sm prose-pre:p-0 max-w-none ${className ?? ""}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks]}
        components={{
          code({ className: codeClassName, children, ...props }) {
            const match = /language-(\w+)/.exec(codeClassName || "");
            const language = match ? match[1] : "";

            if (codeClassName && language) {
              return (
                <SyntaxHighlighter
                  style={oneLight}
                  language={language}
                  PreTag="div"
                  className="rounded-lg text-xs"
                >
                  {String(children).replace(/\n$/, "")}
                </SyntaxHighlighter>
              );
            }

            return (
              <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-800 dark:bg-gray-800 dark:text-gray-200" {...props}>
                {children}
              </code>
            );
          },
          p({ children }) {
            return <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>;
          },
          strong({ children }) {
            return <strong className="font-semibold">{children}</strong>;
          },
          em({ children }) {
            return <em>{children}</em>;
          },
          ul({ children }) {
            return <ul className="mb-2 list-disc pl-5 space-y-0.5">{children}</ul>;
          },
          ol({ children }) {
            return <ol className="mb-2 list-decimal pl-5 space-y-0.5">{children}</ol>;
          },
          li({ children }) {
            return <li className="mb-0.5">{children}</li>;
          },
          h1({ children }) {
            return <h1 className="mb-2 mt-3 text-lg font-bold first:mt-0">{children}</h1>;
          },
          h2({ children }) {
            return <h2 className="mb-2 mt-3 text-base font-bold first:mt-0">{children}</h2>;
          },
          h3({ children }) {
            return <h3 className="mb-1 mt-2 text-sm font-bold first:mt-0">{children}</h3>;
          },
          h4({ children }) {
            return <h4 className="mb-1 mt-2 text-sm font-semibold first:mt-0">{children}</h4>;
          },
          blockquote({ children }) {
            return (
              <blockquote className="mb-2 border-l-[3px] border-gray-300 pl-3 italic text-gray-600 dark:border-gray-600 dark:text-gray-400">
                {children}
              </blockquote>
            );
          },
          a({ children, href }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-500 hover:underline break-all"
              >
                {children}
              </a>
            );
          },
          hr() {
            return <hr className="my-3 border-gray-200 dark:border-gray-700" />;
          },
          /* Tables (GFM) */
          table({ children }) {
            return (
              <div className="my-2 overflow-x-auto">
                <table className="min-w-full border-collapse text-sm">{children}</table>
              </div>
            );
          },
          thead({ children }) {
            return <thead className="bg-gray-50 dark:bg-gray-800">{children}</thead>;
          },
          th({ children }) {
            return (
              <th className="border border-gray-200 px-2 py-1 text-left text-xs font-semibold dark:border-gray-700">
                {children}
              </th>
            );
          },
          td({ children }) {
            return (
              <td className="border border-gray-200 px-2 py-1 dark:border-gray-700">
                {children}
              </td>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
