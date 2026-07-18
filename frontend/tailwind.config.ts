import type { Config } from "tailwindcss";

// Design tokens for AppPulse Analytics.
// Direction: "signal intelligence" - a telemetry/instrument-panel feel that
// matches the product's actual job (reading faint public signals honestly),
// rather than a generic SaaS cream/terracotta or black/acid-green default.
const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        base: {
          DEFAULT: "#0F1219",   // page background, deep graphite-blue
          surface: "#171B25",   // card surface
          raised: "#1E2330",    // hover / raised surface
          border: "#272D3D",
        },
        ink: {
          DEFAULT: "#EDEFF3",   // primary text
          muted: "#8B92A3",     // secondary text
          faint: "#575E70",     // tertiary / disabled
        },
        signal: {
          high: "#3DDC9A",      // high confidence / positive
          mid: "#F2B84B",       // medium confidence
          low: "#F2665B",       // low confidence / negative
          accent: "#5B8CFF",    // brand / interactive accent (links, primary actions)
        },
      },
      fontFamily: {
        display: ["var(--font-display)"],
        body: ["var(--font-body)"],
        mono: ["var(--font-mono)"],
      },
      borderRadius: {
        xl2: "1.25rem",
      },
      boxShadow: {
        panel: "0 1px 0 0 rgba(255,255,255,0.03) inset, 0 8px 24px -12px rgba(0,0,0,0.5)",
      },
    },
  },
  plugins: [],
};

export default config;
