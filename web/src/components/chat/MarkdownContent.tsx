/** Markdown content renderer with syntax highlighting */

import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneLight } from "react-syntax-highlighter/dist/esm/styles/prism";

interface MarkdownContentProps {
  content: string;
}

export function MarkdownContent({ content }: MarkdownContentProps) {
  return (
    <div className="prose prose-sm prose-pre:p-0 max-w-none">
      <ReactMarkdown
        components={{
          code({ className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || "");
            const language = match ? match[1] : "";

            if (className && language) {
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
              <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-800" {...props}>
                {children}
              </code>
            );
          },
          p({ children }) {
            return <p className="mb-2 last:mb-0">{children}</p>;
          },
          ul({ children }) {
            return <ul className="mb-2 list-disc pl-4">{children}</ul>;
          },
          ol({ children }) {
            return <ol className="mb-2 list-decimal pl-4">{children}</ol>;
          },
          li({ children }) {
            return <li className="mb-0.5">{children}</li>;
          },
          h1({ children }) {
            return <h1 className="mb-2 text-lg font-bold">{children}</h1>;
          },
          h2({ children }) {
            return <h2 className="mb-2 text-base font-bold">{children}</h2>;
          },
          h3({ children }) {
            return <h3 className="mb-1 text-sm font-bold">{children}</h3>;
          },
          blockquote({ children }) {
            return (
              <blockquote className="mb-2 border-l-4 border-gray-300 pl-3 italic text-gray-600">
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
                className="text-blue-500 hover:underline"
              >
                {children}
              </a>
            );
          },
          table({ children }) {
            return (
              <div className="mb-2 overflow-x-auto">
                <table className="min-w-full border-collapse text-xs">{children}</table>
              </div>
            );
          },
          thead({ children }) {
            return <thead className="bg-gray-50">{children}</thead>;
          },
          th({ children }) {
            return (
              <th className="border border-gray-200 px-3 py-1.5 text-left font-semibold">
                {children}
              </th>
            );
          },
          td({ children }) {
            return <td className="border border-gray-200 px-3 py-1.5">{children}</td>;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
