export default function KpiCard({
  label,
  value,
  sublabel,
  accent,
}: {
  label: string;
  value: string;
  sublabel?: string;
  accent?: "high" | "mid" | "low" | "accent";
}) {
  const accentClass = accent
    ? {
        high: "text-signal-high",
        mid: "text-signal-mid",
        low: "text-signal-low",
        accent: "text-signal-accent",
      }[accent]
    : "text-ink";

  return (
    <div className="kpi-card">
      <div className="text-xs uppercase tracking-wide text-ink-muted mb-2">{label}</div>
      <div className={`data-figure text-2xl font-medium ${accentClass}`}>{value}</div>
      {sublabel && <div className="text-xs text-ink-faint mt-1">{sublabel}</div>}
    </div>
  );
}
