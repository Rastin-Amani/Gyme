import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/private';
import { faviconFallback, fetchTenantResource } from '$lib/server/tenant-pwa';

export const GET: RequestHandler = async (event) => {
	const response = await fetchTenantResource(event, '/favicon.ico');
	const location = response.headers.get('location');
	if (location && faviconFallback(location, env.BACKEND_URL || 'http://127.0.0.1:8000')) {
		return new Response(null, { status: 302, headers: { Location: '/favicon.svg', 'Cache-Control': 'private, no-cache' } });
	}
	const headers = new Headers({ 'Cache-Control': 'private, no-cache' });
	const contentType = response.headers.get('content-type');
	if (contentType) headers.set('Content-Type', contentType);
	if (location) headers.set('Location', location);
	return new Response(response.body, { status: response.status, headers });
};
