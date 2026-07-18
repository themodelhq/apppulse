const LABELS: Record<string, string> = {
  apple_itunes_api: "Apple iTunes API",
  google_play_scraper_lib: "Google Play",
  raw_html_fallback: "Google Play (fallback reader)",
  appbrain: "AppBrain (independent)",
  wikipedia: "Wikipedia",
};

export default function SourceBadges({ sources }: { sources: string[] }) {
  if (!sources || sources.length === 0) {
    return (
      <span className="text-xs text-signal-low bg-signal-low/10 border border-signal-low/30 rounded-full px-2.5 py-1">
        No source data yet
      </span>
    );
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {sources.map((s) => (
        <span
          key={s}
          className="text-xs text-ink-muted bg-base-raised border border-base-border rounded-full px-2.5 py-1"
        >
          {LABELS[s] ?? s}
        </span>
      ))}
    </div>
  );
}
