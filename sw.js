/* Link Repo service worker.
   Network first, cache as fallback: when online you always get the live file and
   the cache quietly updates behind it; offline you get whatever you saw last.
   Bump CACHE to force every client to drop its old cache on next load. */

const CACHE = 'link-repo-v1';
const SHELL = ['./', './index.html', './links.json', './qr-plain.png', './manifest.json'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  const sameOrigin = url.origin === location.origin;
  const font = url.hostname === 'fonts.googleapis.com' || url.hostname === 'fonts.gstatic.com';
  if (!sameOrigin && !font) return;            // outbound links are not ours to touch

  // the page and its data: strip ?q= and #hash so one cache entry serves every entry point
  const key = sameOrigin && (url.pathname.endsWith('/') || url.pathname.endsWith('/index.html'))
    ? new Request(url.origin + url.pathname.replace(/index\.html$/, ''))
    : req;

  e.respondWith(
    fetch(req).then(res => {
      if (res && (res.ok || res.type === 'opaque')) {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(key, copy));
      }
      return res;
    }).catch(() => caches.match(key).then(hit =>
      hit || (req.mode === 'navigate' ? caches.match('./') : Response.error())
    ))
  );
});
