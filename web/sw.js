/* Service worker: приложение открывается и работает без интернета.
   Стратегии: оболочка — cache-first, API — network-first с возвратом к кэшу. */

const VERSION = 'ttpu-v2.0.5';
const SHELL = `${VERSION}-shell`;
const DATA = `${VERSION}-data`;

const SHELL_ASSETS = [
  '/',
  '/assets/app.css',
  '/assets/app.js',
  '/assets/fonts/fonts.css',
  '/assets/fonts/manrope-cyrillic.woff2',
  '/assets/fonts/manrope-latin.woff2',
  '/assets/fonts/manrope-latin-ext.woff2',
  '/assets/fonts/literata-cyrillic.woff2',
  '/assets/fonts/literata-latin.woff2',
  '/assets/fonts/literata-latin-ext.woff2',
  '/assets/fonts/jetbrains-mono-cyrillic.woff2',
  '/assets/fonts/jetbrains-mono-latin.woff2',
  '/assets/fonts/jetbrains-mono-latin-ext.woff2',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
  '/icons/apple-touch-icon.png',
  '/icons/favicon.png',
  '/manifest.webmanifest',
];

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(SHELL);
    await Promise.all(SHELL_ASSETS.map((url) =>
      cache.add(new Request(url, { cache: 'reload' })).catch(() => null)));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((key) => !key.startsWith(VERSION)).map((key) => caches.delete(key)));
    await self.clients.claim();
  })());
});

self.addEventListener('message', (event) => {
  const data = event.data || {};
  if (data.type === 'cache' && data.url) {
    event.waitUntil(caches.open(DATA).then((cache) =>
      fetch(data.url, { credentials: 'same-origin' }).then((response) => {
        if (response.ok) return cache.put(data.url, response.clone());
        return null;
      }).catch(() => null)));
  }
});

async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const response = await fetch(request);
    if (response && response.ok) cache.put(request, response.clone());
    return response;
  } catch (error) {
    const cached = await cache.match(request);
    if (cached) return cached;
    throw error;
  }
}

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) {
    fetch(request).then((response) => {
      if (response && response.ok) cache.put(request, response.clone());
    }).catch(() => null);
    return cached;
  }
  const response = await fetch(request);
  if (response && response.ok) cache.put(request, response.clone());
  return response;
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (request.mode === 'navigate') {
    event.respondWith((async () => {
      try {
        const response = await fetch(request);
        const cache = await caches.open(SHELL);
        cache.put('/', response.clone());
        return response;
      } catch (error) {
        const cache = await caches.open(SHELL);
        return (await cache.match('/')) || Response.error();
      }
    })());
    return;
  }

  if (url.pathname.startsWith('/api/offline/')) {
    event.respondWith(networkFirst(request, DATA));
    return;
  }

  if (url.pathname.startsWith('/api/')) {
    event.respondWith((async () => {
      try {
        return await fetch(request);
      } catch (error) {
        const cache = await caches.open(DATA);
        return (await cache.match(request)) || Response.error();
      }
    })());
    return;
  }

  if (url.pathname.startsWith('/assets/') || url.pathname.startsWith('/icons/') ||
      url.pathname === '/manifest.webmanifest') {
    event.respondWith(cacheFirst(request, SHELL));
  }
});
