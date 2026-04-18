import type { ReactNode } from "react";

interface PageHeaderProps {
  eyebrow: string;
  title: ReactNode;
  description?: ReactNode;
  meta?: ReactNode;
  actions?: ReactNode;
  children?: ReactNode;
  titleClassName?: string;
  className?: string;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  meta,
  actions,
  children,
  titleClassName,
  className,
}: PageHeaderProps) {
  return (
    <div className={`border-b border-[var(--line)] px-4 py-4 lg:px-6 ${className ?? ""}`}>
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div className="min-w-0 max-w-3xl">
          <div className="flex flex-wrap items-center gap-2">
            <span className="nest-kicker">{eyebrow}</span>
            {meta}
          </div>
          <h2
            className={`nest-title mt-2 text-[1.6rem] font-semibold leading-tight text-[var(--text-strong)] ${
              titleClassName ?? ""
            }`}
          >
            {title}
          </h2>
          {description && (
            <p className="mt-2 text-sm leading-7 text-[var(--text-soft)]">{description}</p>
          )}
        </div>
        {actions && (
          <div className="flex flex-wrap items-center gap-2 xl:justify-end">{actions}</div>
        )}
      </div>
      {children && <div className="mt-5 space-y-4">{children}</div>}
    </div>
  );
}
