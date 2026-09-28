import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/private';
import { fetchTenantResource } from '$lib/server/tenant-pwa';

export const GET: RequestHandler = async (event) => {
	const response = await fetchTenantResource(event, '/manifest.json');
	if (!response.ok) return new Response(null, { status: response.status });

	const manifest = await response.json();
	const backend = (env.BACKEND_URL || 'http://backend:8000').replace(/\/+$/, '');
	const backendOrigin = new URL(backend).origin;
	for (const icon of manifest.icons ?? []) {
		const source = new URL(icon.src, event.url);
		if (
			source.pathname.startsWith('/static/icons/') &&
			(icon.src.startsWith('/static/icons/') || source.origin === backendOrigin)
		) {
			icon.src = '/favicon.svg';
			icon.type = 'image/svg+xml';
			icon.sizes = 'any';
		}
	}
	return Response.json(manifest, {
		headers: { 'Cache-Control': 'private, no-cache', 'Content-Type': 'application/manifest+json' }
	});
};
