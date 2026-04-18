import type { LucideIcon } from "lucide-react";

export interface SlidingNavItem {
  key: string;
  label: string;
  icon?: LucideIcon;
}

interface SlidingNavProps {
  items: SlidingNavItem[];
  activeKey: string;
  onChange: (key: string) => void;
  className?: string;
}

export function SlidingNav({ items, activeKey, onChange, className }: SlidingNavProps) {
  const activeIndex = Math.max(
    items.findIndex((item) => item.key === activeKey),
    0
  );

  return (
    <div
      className={`nest-nav-strip ${className ?? ""}`}
      style={
        {
          ["--nav-active-index" as any]: activeIndex,
          ["--nav-count" as any]: items.length,
        } as React.CSSProperties
      }
    >
      {items.map((item) => (
        <button
          key={item.key}
          onClick={() => onChange(item.key)}
          className={`nest-nav-pill ${activeKey === item.key ? "nest-nav-pill-active" : ""}`}
          title={item.label}
        >
          {item.icon && <item.icon size={14} />}
          <span>{item.label}</span>
        </button>
      ))}
    </div>
  );
}
