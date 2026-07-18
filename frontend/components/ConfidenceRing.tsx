"use client";

function colorFor(pct: number | null): string {
  if (pct === null) return "#575E70";
  if (pct >= 55) return "#3DDC9A"; // high
  if (pct >= 30) return "#F2B84B"; // mid
  return "#F2665B"; // low
}

export default function ConfidenceRing({
  confidencePct,
  size = 64,
  thickness = 6,
  children,
}: {
  confidencePct: number | null;
  size?: number;
  thickness?: number;
  children?: React.ReactNode;
}) {
  const pct = confidencePct ?? 0;
  const color = colorFor(confidencePct);

  return (
    <div
      className="confidence-ring"
      style={{
        width: size,
        height: size,
        // @ts-expect-error - CSS custom properties
        "--pct": pct,
        "--ring-color": color,
      }}
      title={confidencePct !== null ? `${confidencePct.toFixed(0)}% confidence` : "No confidence data yet"}
    >
      <div
        className="confidence-ring-inner"
        style={{ width: size - thickness * 2, height: size - thickness * 2 }}
      >
        {children ?? (
          <span className="text-[11px] font-mono font-medium" style={{ color }}>
            {confidencePct !== null ? `${Math.round(confidencePct)}%` : "—"}
          </span>
        )}
      </div>
    </div>
  );
}
