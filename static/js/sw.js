// static/js/sw.js
const CACHE_NAME = "attendance-cache-v1";
const urlsToCache = [
  "/",
  "/static/css/app.css",
  "/static/js/dashboard-charts.js",
];

self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener("fetch", e => {
  e.respondWith(
    caches.match(e.request).then(response => response || fetch(e.request))
  );
});
