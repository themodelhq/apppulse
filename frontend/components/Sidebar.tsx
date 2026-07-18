"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, PlusCircle, Bell, Radio } from "lucide-react";
import clsx from "clsx";

const links = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/add", label: "Track an app", icon: PlusCircle },
  { href: "/alerts", label: "Alerts", icon: Bell },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 shrink-0 border-r border-base-border bg-base-surface/60 hidden md:flex flex-col">
      <div className="px-6 py-6 flex items-center gap-2.5">
        <Radio className="w-5 h-5 text-signal-accent" />
        <span className="font-display font-bold text-lg tracking-tight">AppPulse</span>
      </div>

      <nav className="px-3 flex-1">
        {links.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm mb-1 transition-colors",
                active
                  ? "bg-base-raised text-ink"
                  : "text-ink-muted hover:text-ink hover:bg-base-raised/60"
              )}
            >
              <Icon className="w-4 h-4" />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="px-6 py-5 text-xs text-ink-faint leading-relaxed border-t border-base-border">
        Estimates are modeled from public signals, not official figures.
      </div>
    </aside>
  );
}
