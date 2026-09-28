import { build, files, version } from '$service-worker';

const cacheName = `gyme-static-${version}`;
const assets = [...build, ...files];

self.addEventListener('install', (event) => {
	event.waitUntil(caches.open(cacheName).then((cache) => cache.addAll(assets)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
	event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((key) => key.startsWith('gyme-static-') && key !== cacheName).map((key) => caches.delete(key)))).then(() => self.clients.claim()));
});

self.addEventListener('fetch', (event) => {
	const request = event.request;
	const url = new URL(request.url);
	if (request.method !== 'GET' || url.origin !== location.origin || url.pathname.startsWith('/api/')) return;
	if (request.mode === 'navigate') {
		event.respondWith(fetch(request).catch(async () => (await caches.match('/offline.html')) ?? Response.error()));
		return;
	}
	event.respondWith(caches.match(request).then((cached) => cached ?? fetch(request)));
});
