/* Cove · service worker
 * 只缓存"永远不会变"的图标与清单；入口 HTML 和 JS/CSS 一律走网络。
 * 原因：入口 HTML 一旦被缓存，发版后浏览器就会拿着旧入口去引用已经不存在的
 * 旧 JS/CSS，表现就是整页白屏、或者"改了但看着一模一样"。这比省一点流量重要得多。
 */
const VERSION = 'cove-v7';
const CORE = ['./manifest.webmanifest', './icon.svg', './icon-180.png', './icon-192.png', './icon-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(VERSION)
      .then(c => c.addAll(CORE).catch(() => {}))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;      // 第三方请求不接管
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/uploads/')) return; // 业务接口直连

  const isDoc = req.mode === 'navigate' ||
                (req.headers.get('accept') || '').includes('text/html');

  /* 入口与代码：直接走网络，绝不回旧缓存。
     拿不到网络就明确失败，宁可报错也不给一份已经对不上的旧页面。 */
  if (isDoc || url.pathname.startsWith('/assets/')) {
    e.respondWith(fetch(req, { cache: 'no-store' }).catch(() => new Response('', { status: 503 })));
    return;
  }

  /* 图标 / 清单这类真不会变的，才走缓存 */
  e.respondWith(
    caches.match(req).then(hit => hit || fetch(req).then(res => {
      if (res.ok && res.type === 'basic') {
        const copy = res.clone();
        caches.open(VERSION).then(c => c.put(req, copy)).catch(() => {});
      }
      return res;
    }))
  );
});
