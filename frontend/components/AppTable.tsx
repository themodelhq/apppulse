"use client";

import Link from "next/link";
import Image from "next/image";
import { Star, Smartphone } from "lucide-react";
import type { AppSummary } from "@/lib/api";

export default function AppTable({ apps }: { apps: AppSummary[] }) {
  if (apps.length === 0) {
    return (
      <div className="kpi-card text-center py-12 text-ink-muted">
        No apps tracked yet.{" "}
        <Link href="/add" className="text-signal-accent hover:underline">
          Add your first one
        </Link>
        .
      </div>
    );
  }

  return (
    <div className="kpi-card p-0 overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-ink-muted text-xs uppercase tracking-wide border-b border-base-border">
            <th className="px-5 py-3 font-medium">App</th>
            <th className="px-5 py-3 font-medium">Store</th>
            <th className="px-5 py-3 font-medium">Category</th>
            <th className="px-5 py-3 font-medium">Version</th>
            <th className="px-5 py-3 font-medium">Updated</th>
          </tr>
        </thead>
        <tbody>
          {apps.map((app) => (
            <tr
              key={app.id}
              className="border-b border-base-border last:border-0 hover:bg-base-raised/50 transition-colors"
            >
              <td className="px-5 py-3">
                <Link href={`/apps/${app.id}`} className="flex items-center gap-3 min-w-0">
                  {app.icon_url ? (
                    <Image
                      src={app.icon_url}
                      alt=""
                      width={32}
                      height={32}
                      className="rounded-lg shrink-0"
                    />
                  ) : (
                    <div className="w-8 h-8 rounded-lg bg-base-raised grid place-items-center shrink-0">
                      <Smartphone className="w-4 h-4 text-ink-faint" />
                    </div>
                  )}
                  <span className="truncate">
                    <span className="text-ink font-medium">{app.name ?? "Fetching…"}</span>
                    {app.is_favorite && (
                      <Star className="inline w-3.5 h-3.5 ml-1.5 text-signal-mid fill-signal-mid" />
                    )}
                    <span className="block text-xs text-ink-faint truncate">{app.developer}</span>
                  </span>
                </Link>
              </td>
              <td className="px-5 py-3 text-ink-muted">
                {app.store === "apple_app_store" ? "App Store" : "Google Play"}
              </td>
              <td className="px-5 py-3 text-ink-muted">{app.category ?? "—"}</td>
              <td className="px-5 py-3 text-ink-muted data-figure">{app.version ?? "—"}</td>
              <td className="px-5 py-3 text-ink-faint text-xs">
                {app.updated_at ? new Date(app.updated_at).toLocaleString() : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
