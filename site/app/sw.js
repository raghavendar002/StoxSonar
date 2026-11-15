// StoxSonar app service worker: offline shell, fresh data first, and push alerts.
const SHELL = "stoxsonar-shell-v2";
const DATA = "stoxsonar-data";
const SHELL_FILES = ["./", "index.html", "app.css", "manifest.webmanifest", "vapid.json", "icon-192.png", "apple-touch-icon.png",
                     "js/main.js", "js/core.js", "js/charts.js", "js/views.js", "js/sim.js", "js/more.js"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(SHELL).then((c) => c.addAll(SHELL_FILES)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys()
    .then((keys) => Promise.all(keys.filter((k) => k !== SHELL && k !== DATA).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return;
  if (url.pathname.endsWith(".json") && !url.pathname.endsWith("vapid.json")) {
    // Data: always try the network, fall back to the last copy when offline
    e.respondWith(fetch(e.request, { cache: "no-store" }).then((r) => {
      if (r.ok) { const copy = r.clone(); caches.open(DATA).then((c) => c.put(url.pathname, copy)); }
      return r;
    }).catch(() => caches.open(DATA).then((c) => c.match(url.pathname))
      .then((r) => r || new Response("{}", { status: 503 }))));
    return;
  }
  // Shell: network first so updates land, cache when offline
  e.respondWith(fetch(e.request).then((r) => {
    if (r.ok && url.pathname.includes("/app/")) { const copy = r.clone(); caches.open(SHELL).then((c) => c.put(e.request, copy)); }
    return r;
  }).catch(() => caches.match(e.request, { ignoreSearch: true })));
});

// iOS revokes a subscription that receives pushes without showing them, so always show one
self.addEventListener("push", (e) => {
  let m = { title: "StoxSonar", body: "New data is out.", url: "./" };
  try { if (e.data) m = Object.assign(m, e.data.json()); } catch (_) { if (e.data) m.body = e.data.text(); }
  e.waitUntil(self.registration.showNotification(m.title, {
    body: m.body, tag: m.tag || undefined, icon: "icon-192.png", badge: "icon-192.png",
    data: { url: new URL(m.url || "./", self.registration.scope).href },
  }));
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const target = (e.notification.data && e.notification.data.url) || self.registration.scope;
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((wins) => {
    for (const w of wins) { if (w.url.startsWith(self.registration.scope)) { w.navigate(target); return w.focus(); } }
    return self.clients.openWindow(target);
  }));
});
