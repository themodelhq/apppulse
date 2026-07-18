"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { AlertTriangle } from "lucide-react";

export default function AlertsPage() {
  const { data: alerts, isLoading } = useQuery({
    queryKey: ["alerts"],
    queryFn: api.getAlerts,
    refetchInterval: 45_000,
  });

  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      <h1 className="font-display text-2xl font-bold tracking-tight mb-1">Alerts</h1>
      <p className="text-ink-muted text-sm mb-8">
        Rating drops, review spikes, and estimate swings across your tracked apps.
      </p>

      {isLoading ? (
        <div className="kpi-card py-12 text-center text-ink-muted">Loading…</div>
      ) : !alerts || alerts.length === 0 ? (
        <div className="kpi-card py-12 text-center text-ink-muted">No alerts yet.</div>
      ) : (
        <div className="space-y-2">
          {alerts.map((a) => (
            <div key={a.id} className="kpi-card flex items-start gap-3 py-4">
              <AlertTriangle className="w-4 h-4 mt-0.5 text-signal-mid shrink-0" />
              <div>
                <div className="text-sm">{a.message}</div>
                <div className="text-xs text-ink-faint mt-1">
                  {new Date(a.created_at).toLocaleString()}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
