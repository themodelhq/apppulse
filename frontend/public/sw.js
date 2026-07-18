const CACHE_NAME = "apppulse-v2"; // bumped: forces old cached app-shell/JS bundles to be
                                    // discarded on the next deploy, so a stale build (e.g.
                                    // one baked with the wrong API URL) can't linger in a
                                    // browser's cache after you've fixed the env var and
                                    // redeployed.
const PRECACHE_URLS = ["/", "/manifest.json"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Network-first for API calls (freshness matters), cache-first for
// everything else (app shell, static assets) so the dashboard still opens
// offline, even if data is stale.
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      fetch(event.request)
        .then((res) => {
          const clone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          return res;
        })
        .catch(async () => {
          // caches.match() resolves to `undefined` on a miss - passing that
          // straight to respondWith() throws "Failed to convert value to
          // 'Response'" and shows up as a confusing, unrelated-looking
          // console error on top of whatever actually failed. Always
          // resolve to a real Response instead.
          const cached = await caches.match(event.request);
          return (
            cached ||
            new Response(JSON.stringify({ error: "offline", detail: "No network and no cached response available." }), {
              status: 503,
              headers: { "Content-Type": "application/json" },
            })
          );
        })
    );
    return;
  }

  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
