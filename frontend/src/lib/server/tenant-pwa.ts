import { env } from '$env/dynamic/private';
import type { RequestEvent } from '@sveltejs/kit';

export async function fetchTenantResource(event: RequestEvent, path: string) {
	const backend = (env.BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');
	const headers = new Headers({
		'X-Forwarded-Host': event.url.host,
		'X-Forwarded-Proto': event.url.protocol.slice(0, -1)
	});
	const cookie = event.request.headers.get('cookie');
	if (cookie) headers.set('cookie', cookie);
	try {
		headers.set('X-Real-Client-IP', event.getClientAddress());
	} catch {
		headers.set('X-Real-Client-IP', 'unknown');
	}
	return globalThis.fetch(`${backend}${path}`, { headers, redirect: 'manual' });
}

export function faviconFallback(location: string, backend: string) {
	const target = new URL(location, backend);
	return target.origin === new URL(backend).origin && target.pathname.startsWith('/static/icons/');
}
