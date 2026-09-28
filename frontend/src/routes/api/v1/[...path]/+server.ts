import { env } from '$env/dynamic/private';
import type { RequestHandler } from './$types';

const hopByHop = new Set([
	'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te',
	'trailers', 'transfer-encoding', 'upgrade', 'host', 'content-length'
]);
const forwarded = new Set([
	'accept', 'accept-language', 'content-type', 'cookie', 'if-match', 'if-none-match',
	'range', 'user-agent', 'x-requested-with', 'origin', 'referer'
]);

const proxy: RequestHandler = async ({ request, params, url, getClientAddress }) => {
	const backend = (env.BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');
	if (!params.path || params.path.split('/').some((part) => !part || part === '.' || part === '..' || /[%\\]/.test(part))) {
		return new Response('Invalid API path', { status: 400 });
	}
	const headers = new Headers();
	for (const [name, value] of request.headers) {
		if (forwarded.has(name.toLowerCase()) && !hopByHop.has(name.toLowerCase())) headers.set(name, value);
	}
	headers.set('x-forwarded-host', url.host);
	headers.set('x-forwarded-proto', url.protocol.slice(0, -1));
	try {
		headers.set('x-real-client-ip', getClientAddress());
	} catch {
		headers.set('x-real-client-ip', 'unknown');
	}
	const target = `${backend}/api/v1/${params.path}${url.search}`;
	const init: RequestInit = {
		method: request.method,
		headers,
		redirect: 'manual'
	};
	if (request.method !== 'GET' && request.method !== 'HEAD') init.body = await request.arrayBuffer();
	let upstream: Response;
	try {
		upstream = await globalThis.fetch(target, init);
	} catch {
		return Response.json({ detail: 'Backend API is unavailable.' }, { status: 502 });
	}
	const responseHeaders = new Headers();
	for (const [name, value] of upstream.headers) {
		if (!hopByHop.has(name.toLowerCase()) && name.toLowerCase() !== 'set-cookie') responseHeaders.append(name, value);
	}
	for (const cookie of upstream.headers.getSetCookie?.() ?? []) {
		let normalized = cookie.replace(/;\s*domain=[^;]+/i, '').replace(/;\s*path=[^;]*/i, '; Path=/');
		if (!/;\s*path=/i.test(normalized)) normalized += '; Path=/';
		responseHeaders.append('set-cookie', normalized);
	}
	return new Response(upstream.body, { status: upstream.status, statusText: upstream.statusText, headers: responseHeaders });
};

export const GET = proxy;
export const HEAD = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const OPTIONS = proxy;
