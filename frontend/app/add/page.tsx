"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, Store } from "@/lib/api";
import { Apple, PlayCircle } from "lucide-react";
import clsx from "clsx";

export default function AddAppPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [store, setStore] = useState<Store>("apple_app_store");
  const [storeId, setStoreId] = useState("");
  const [country, setCountry] = useState("us");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => api.addApp({ store, store_id: storeId.trim(), country }),
    onSuccess: (app) => {
      queryClient.invalidateQueries({ queryKey: ["apps"] });
      router.push(`/apps/${app.id}`);
    },
    onError: (err: Error) => setError(err.message),
  });

  return (
    <div className="max-w-xl mx-auto px-6 py-8">
      <h1 className="font-display text-2xl font-bold tracking-tight mb-1">Track an app</h1>
      <p className="text-ink-muted text-sm mb-8">
        Add an app by its Apple numeric ID or Google Play package name. AppPulse fetches metadata
        immediately and starts polling on the refresh schedule after that.
      </p>

      <div className="kpi-card space-y-5">
        <div>
          <label className="text-xs uppercase tracking-wide text-ink-muted mb-2 block">Store</label>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setStore("apple_app_store")}
              className={clsx(
                "flex items-center gap-2 justify-center px-4 py-3 rounded-lg border text-sm transition-colors",
                store === "apple_app_store"
                  ? "border-signal-accent bg-signal-accent/10 text-ink"
                  : "border-base-border text-ink-muted hover:bg-base-raised"
              )}
            >
              <Apple className="w-4 h-4" /> App Store
            </button>
            <button
              type="button"
              onClick={() => setStore("google_play")}
              className={clsx(
                "flex items-center gap-2 justify-center px-4 py-3 rounded-lg border text-sm transition-colors",
                store === "google_play"
                  ? "border-signal-accent bg-signal-accent/10 text-ink"
                  : "border-base-border text-ink-muted hover:bg-base-raised"
              )}
            >
              <PlayCircle className="w-4 h-4" /> Google Play
            </button>
          </div>
        </div>

        <div>
          <label className="text-xs uppercase tracking-wide text-ink-muted mb-2 block">
            {store === "apple_app_store" ? "Numeric App ID" : "Package name"}
          </label>
          <input
            value={storeId}
            onChange={(e) => setStoreId(e.target.value)}
            placeholder={store === "apple_app_store" ? "e.g. 284882215 (Facebook)" : "e.g. com.spotify.music"}
            className="w-full bg-base-raised border border-base-border rounded-lg px-3 py-2.5 text-sm outline-none focus:border-signal-accent"
          />
          <p className="text-xs text-ink-faint mt-2">
            {store === "apple_app_store"
              ? "Find this in the App Store URL: apps.apple.com/us/app/name/id284882215 → the number after \"id\"."
              : "Find this in the Play Store URL: play.google.com/store/apps/details?id=com.spotify.music"}
          </p>
        </div>

        <div>
          <label className="text-xs uppercase tracking-wide text-ink-muted mb-2 block">
            Storefront country
          </label>
          <input
            value={country}
            onChange={(e) => setCountry(e.target.value.toLowerCase())}
            maxLength={2}
            className="w-24 bg-base-raised border border-base-border rounded-lg px-3 py-2.5 text-sm outline-none focus:border-signal-accent uppercase"
          />
        </div>

        {error && (
          <div className="text-signal-low text-sm bg-signal-low/10 border border-signal-low/30 rounded-lg px-3 py-2">
            {error}
          </div>
        )}

        <button
          type="button"
          disabled={!storeId.trim() || mutation.isPending}
          onClick={() => {
            setError(null);
            mutation.mutate();
          }}
          className="w-full bg-signal-accent text-base font-medium rounded-lg py-2.5 text-sm disabled:opacity-40 hover:opacity-90 transition-opacity"
        >
          {mutation.isPending ? "Adding…" : "Start tracking"}
        </button>
      </div>
    </div>
  );
}
