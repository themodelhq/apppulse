"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useLiveUpdates } from "@/lib/useLiveUpdates";
import KpiCard from "@/components/KpiCard";
import AppTable from "@/components/AppTable";
import clsx from "clsx";

function formatNumber(n: number | null | undefined): string {
  if (n === null || n === undefined) return "—";
  return new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 }).format(n);
}

export default function DashboardPage() {
  const { connected, lastUpdate } = useLiveUpdates();

  const { data: kpis, isLoading: kpisLoading } = useQuery({
    queryKey: ["kpis"],
    queryFn: api.getKpis,
    refetchInterval: 45_000,
  });

  const { data: apps, isLoading: appsLoading } = useQuery({
    queryKey: ["apps"],
    queryFn: () => api.listApps({}),
    refetchInterval: 45_000,
  });

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      <header className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-display text-2xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-ink-muted text-sm mt-1">
            Estimated downloads are modeled from public signals — see each app&apos;s confidence score.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-ink-muted">
          <span
            className={clsx(
              "w-2 h-2 rounded-full",
              connected ? "bg-signal-high live-dot" : "bg-ink-faint"
            )}
          />
          {connected ? "Live" : "Reconnecting…"}
          {lastUpdate && (
            <span className="text-ink-faint">
              · last refresh {new Date(lastUpdate).toLocaleTimeString()}
            </span>
          )}
        </div>
      </header>

      <section className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 mb-8">
        <KpiCard
          label="Apps tracked"
          value={kpisLoading ? "…" : String(kpis?.total_apps_tracked ?? 0)}
        />
        <KpiCard
          label="Today's est. downloads"
          value={kpisLoading ? "…" : formatNumber(kpis?.today_estimated_downloads)}
          accent="accent"
        />
        <KpiCard
          label="Yesterday's est. downloads"
          value={kpisLoading ? "…" : formatNumber(kpis?.yesterday_estimated_downloads)}
        />
        <KpiCard
          label="30-day est. downloads"
          value={kpisLoading ? "…" : formatNumber(kpis?.thirty_day_estimated_downloads)}
        />
        <KpiCard
          label="Average rating"
          value={kpisLoading ? "…" : kpis?.average_rating?.toFixed(2) ?? "—"}
          accent="mid"
        />
        <KpiCard
          label="Reviews today"
          value={kpisLoading ? "…" : formatNumber(kpis?.reviews_today)}
        />
        <KpiCard
          label="Countries monitored"
          value={kpisLoading ? "…" : String(kpis?.countries_monitored ?? 0)}
        />
        <KpiCard
          label="Alerts today"
          value={kpisLoading ? "…" : String(kpis?.alerts_triggered_today ?? 0)}
          accent={kpis?.alerts_triggered_today ? "low" : undefined}
        />
      </section>

      <section>
        <h2 className="font-display font-semibold text-lg mb-4">Tracked apps</h2>
        {appsLoading ? (
          <div className="kpi-card py-12 text-center text-ink-muted">Loading…</div>
        ) : (
          <AppTable apps={apps ?? []} />
        )}
      </section>
    </div>
  );
}
