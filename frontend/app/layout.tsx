import type { Metadata, Viewport } from "next";
import { Space_Grotesk, Inter, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import QueryProvider from "@/components/QueryProvider";
import ServiceWorkerRegister from "@/components/ServiceWorkerRegister";

const display = Space_Grotesk({ subsets: ["latin"], variable: "--font-display", weight: ["500", "700"] });
const body = Inter({ subsets: ["latin"], variable: "--font-body" });
const mono = IBM_Plex_Mono({ subsets: ["latin"], variable: "--font-mono", weight: ["400", "500"] });

// Every page in this app is a client component that fetches its own data -
// there's nothing here that benefits from static prerendering. Forcing
// dynamic rendering (set here so it applies to every route under this
// layout) stops Netlify's edge CDN from caching the HTML shell as a static
// asset. That caching is what caused the live site to keep serving an old
// HTML shell referencing JS chunk filenames from a previous deploy, even
// after new deploys had already deleted those exact files - a stale
// document, not a stale browser cache.
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "AppPulse Analytics",
  description: "Real-time App Store & Google Play intelligence — honestly estimated.",
  manifest: "/manifest.json",
};

export const viewport: Viewport = {
  themeColor: "#0F1219",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable} ${mono.variable}`}>
      <body>
        <QueryProvider>
          <ServiceWorkerRegister />
          <div className="flex min-h-screen">
            <Sidebar />
            <main className="flex-1 min-w-0">{children}</main>
          </div>
        </QueryProvider>
      </body>
    </html>
  );
}
