// Service Worker for AIN-AI (Offline PWA Queue & Cache - Module M03, AC-M03-6)
const CACHE_NAME = 'ain-ai-v1';
const STATIC_ASSETS = [
  '/documents/upload',
  '/static/fonts.css',
  '/static/documents_upload.html'
];

self.addEventListener('install', (event) => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch(() => {});
    })
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  // Let browser handle API calls directly; network failure triggers client-side IndexedDB queue
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
