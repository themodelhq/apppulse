"use client";

import { useParams } from "next/navigation";
import Image from "next/image";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import ConfidenceRing from "@/components/ConfidenceRing";
import SourceBadges from "@/components/SourceBadges";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { RefreshCw, Star, Smartphone, ExternalLink } from "lucide-react";

export default function AppDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const { data: app, isLoading } = useQuery({
    queryKey: ["apps", id],
    queryFn: () => api.getApp(id),
    refetchInterval: 45_000,
  });

  const refresh = useMutation({
    mutationFn: () => api.refreshApp(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["apps", id] }),
  });

  const favorite = useMutation({
    mutationFn: (is_favorite: boolean) => api.updateApp(id, { is_favorite }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["apps", id] });
      queryClient.invalidateQueries({ queryKey: ["apps"] });
    },
  });

  if (isLoading || !app) {
    return <div className="max-w-4xl mx-auto px-6 py-8 text-ink-muted">Loading…</div>;
  }

  const chartData = app.history.map((s) => ({
    time: new Date(s.fetched_at).toLocaleDateString(undefined, { month: "short", day: "numeric" }),
    rating: s.rating,
    reviews: s.rating_count,
    installs: s.install_bucket_min,
  }));

  const est = app.latest_estimate;

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="flex items-start justify-between mb-8">
        <div className="flex items-center gap-4">
          {app.icon_url ? (
            <Image src={app.icon_url} alt="" width={56} height={56} className="rounded-xl2" />
          ) : (
            <div className="w-14 h-14 rounded-xl2 bg-base-raised grid place-items-center">
              <Smartphone className="w-6 h-6 text-ink-faint" />
            </div>
          )}
          <div>
            <h1 className="font-display text-xl font-bold">{app.name ?? "Fetching…"}</h1>
            <p className="text-ink-muted text-sm">
              {app.developer} · {app.category ?? "Uncategorized"} ·{" "}
              {app.store === "apple_app_store" ? "App Store" : "Google Play"} ({app.country.toUpperCase()})
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => favorite.mutate(!app.is_favorite)}
            className="p-2 rounded-lg border border-base-border hover:bg-base-raised"
            title="Toggle favorite"
          >
            <Star className={`w-4 h-4 ${app.is_favorite ? "fill-signal-mid text-signal-mid" : "text-ink-muted"}`} />
          </button>
          <button
            onClick={() => refresh.mutate()}
            disabled={refresh.isPending}
            className="flex items-center gap-2 px-3 py-2 rounded-lg border border-base-border hover:bg-base-raised text-sm"
          >
            <RefreshCw className={`w-4 h-4 ${refresh.isPending ? "animate-spin" : ""}`} />
            Refresh now
          </button>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-4 mb-8">
        <div className="kpi-card md:col-span-2 flex items-center gap-5">
          <ConfidenceRing confidencePct={est?.confidence_pct ?? null} size={80} thickness={7} />
          <div>
            <div className="text-xs uppercase tracking-wide text-ink-muted mb-1">
              Estimated daily downloads
            </div>
            <div className="data-figure text-3xl font-medium">
              {est?.estimated_daily_downloads !== null && est?.estimated_daily_downloads !== undefined
                ? est.estimated_daily_downloads.toLocaleString()
                : "Gathering data…"}
            </div>
            {est?.low_bound !== null && est?.low_bound !== undefined && (
              <div className="text-xs text-ink-faint mt-1 data-figure">
                Range: {est.low_bound.toLocaleString()} – {est.high_bound?.toLocaleString()}
              </div>
            )}
          </div>
        </div>
        <div className="kpi-card">
          <div className="text-xs uppercase tracking-wide text-ink-muted mb-2">Rating</div>
          <div className="data-figure text-2xl font-medium">
            {app.latest_snapshot?.rating?.toFixed(2) ?? "—"}
          </div>
          <div className="text-xs text-ink-faint mt-1">
            {app.latest_snapshot?.rating_count?.toLocaleString() ?? "—"} ratings
          </div>
        </div>
      </div>

      {est?.notes && (
        <div className="text-xs text-ink-muted bg-base-surface border border-base-border rounded-lg px-4 py-3 mb-4">
          <span className="font-medium text-ink">How this was estimated: </span>
          {est.notes}
        </div>
      )}

      <div className="mb-8">
        <div className="text-xs uppercase tracking-wide text-ink-muted mb-2">
          Data sources used this cycle
        </div>
        <SourceBadges sources={app.latest_snapshot?.sources ?? []} />
      </div>

      {app.milestones.length > 0 && (
        <section className="mb-8">
          <h2 className="font-display font-semibold text-lg mb-4">Reported milestones</h2>
          <div className="space-y-2">
            {app.milestones.slice(0, 3).map((m, i) => (
              <div key={i} className="kpi-card py-4">
                <div className="flex items-center justify-between mb-1">
                  <span className="data-figure text-lg font-medium">
                    {m.reported_downloads?.toLocaleString()} downloads
                  </span>
                  <a
                    href={m.source_url ?? "#"}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1 text-xs text-signal-accent hover:underline"
                  >
                    {m.source} <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
                <p className="text-xs text-ink-muted">{m.context}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="mb-8">
        <h2 className="font-display font-semibold text-lg mb-4">Rating history</h2>
        <div className="kpi-card h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="ratingGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#5B8CFF" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="#5B8CFF" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#272D3D" strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="time" stroke="#575E70" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis
                domain={[0, 5]}
                stroke="#575E70"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                width={28}
              />
              <Tooltip
                contentStyle={{
                  background: "#171B25",
                  border: "1px solid #272D3D",
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <Area type="monotone" dataKey="rating" stroke="#5B8CFF" fill="url(#ratingGradient)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </section>
    </div>
  );
}
