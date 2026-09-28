import { error, fail, isHttpError, isRedirect, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import { api, ApiError, record, records, safeUser, stripSecrets } from '$lib/api';

const isPublicPath = (path: string) => path === '/login' || path === '/logout';

function routeApi(path: string, search: URLSearchParams): string | null {
	if (path === '/dashboard') return `dashboard?${search}`;
	if (path === '/dashboard/coach-stats') return `dashboard/coach-stats?${search}`;
	if (path === '/trainees' || path === '/trainees/search' || path === '/trainees/filter') return `trainees?${search}`;
	if (path === '/coaches') return `coaches?${search}`;
	if (path === '/plans') return `plans?${search}`;
	if (path === '/templates') {
		const params = new URLSearchParams(search);
		params.set('is_template', 'true');
		return `plans?${params}`;
	}
	if (['/trainees/new', '/coaches/new', '/plans/new', '/items/new'].includes(path)) return null;
	let match = path.match(/^\/(trainees|coaches|plans|progress-log|items)\/([^/]+)(?:\/(edit|apply))?$/);
	if (match) {
		const [, kind, id, suffix] = match;
		if (kind === 'progress-log') return `progress-logs/${id}`;
		if (kind === 'items') return `items/${id}${search.size ? `?${search}` : ''}`;
		if (suffix === 'apply') return `plans/${id}`;
		return `${kind}/${id}`;
	}
	if (path === '/user/dashboard') return 'user/dashboard';
	if (path === '/user/plans') return 'user/plans';
	match = path.match(/^\/user\/plans\/([^/]+)$/);
	if (match) return `user/plans/${match[1]}`;
	if (path === '/profile' || path === '/user/profile' || path === '/change-password') return 'auth/me';
	match = path.match(/^\/progress-log\/new\/([^/]+)$/);
	if (match) return `trainees/${match[1]}`;
	return null;
}

export const load: PageServerLoad = async (event) => {
	const path = event.url.pathname.replace(/\/$/, '') || '/';
	const localeQuery = event.url.searchParams.get('locale');
	const supported = ['en', 'es', 'tr', 'hy'];
	const locale = supported.includes(localeQuery ?? '')
		? localeQuery!
		: supported.includes(event.cookies.get('gyme_locale') ?? '')
			? event.cookies.get('gyme_locale')!
			: 'en';
	if (path === '/') throw redirect(307, '/dashboard');
	if (path === '/logout') {
		try { await api(event.fetch, 'auth/logout', { method: 'POST' }); } catch { /* Logout still clears this browser session. */ }
		event.cookies.delete('pb_auth', { path: '/' });
		throw redirect(303, '/login');
	}
	if (path === '/login') {
		try {
			const { data } = await api<any>(event.fetch, 'auth/me');
			const user = safeUser(data);
			if (user) throw redirect(303, user.role === 'trainee' ? '/user/dashboard' : '/dashboard');
		} catch (cause) {
			if (isRedirect(cause)) throw cause;
			if (!(cause instanceof ApiError) || cause.status !== 401) {
				throw error(cause instanceof ApiError ? cause.status : 503, cause instanceof Error ? cause.message : 'Unable to reach the service.');
			}
		}
		return { path, locale, user: null, resource: null, lists: {}, error: null };
	}
	try {
		const { data: me } = await api<any>(event.fetch, 'auth/me');
		const user = safeUser(me);
		if (!user) throw new ApiError(401, 'Please sign in to continue.');
		const endpoint = routeApi(path, event.url.searchParams);
		const formPath = ['/trainees/new', '/coaches/new', '/plans/new', '/items/new'].includes(path)
			|| /^\/templates\/[^/]+\/apply$/.test(path)
			|| /^\/progress-log\/new\/[^/]+$/.test(path);
		if (!endpoint && !formPath) throw error(404, 'Page not found');
		let resource: any = null;
		const lists: Record<string, any> = {};
		if (endpoint) {
			const { data } = await api<any>(event.fetch, endpoint);
			resource = stripSecrets(data);
			if (endpoint === 'auth/me') resource = user;
		}
		if (/^\/plans\/new$/.test(path) || /^\/templates\/[^/]+\/apply$/.test(path)) {
			const [trainees, coaches] = await Promise.all([
				api<any>(event.fetch, 'trainees?per_page=100').then((r) => r.data),
				api<any>(event.fetch, 'coaches?per_page=100').then((r) => r.data)
			]);
			lists.trainees = records(trainees);
			lists.coaches = records(coaches);
		}
		if (path === '/plans') {
			const result = await api<any>(event.fetch, 'coaches?per_page=100').catch(() => null);
			lists.coaches = records(result?.data);
		}
		if (/^\/plans\/new$/.test(path)) {
			const template = event.url.searchParams.get('template') === 'true';
			return { path, locale, user, resource, lists, isTemplate: template, error: null };
		}
		if (/^\/templates\/([^/]+)\/apply$/.test(path)) {
			const id = path.split('/')[2];
			const { data: template } = await api<any>(event.fetch, `plans/${id}`);
			return { path, locale, user, resource: record(template), lists, isTemplate: false, error: null };
		}
		if (path === '/items/new') {
			const planId = event.url.searchParams.get('plan_id');
			if (planId) {
				const { data } = await api<any>(event.fetch, `plans/${planId}`);
				resource = record(data);
			}
		}
		const newLog = path.match(/^\/progress-log\/new\/([^/]+)$/);
		if (newLog) {
			const { data } = await api<any>(event.fetch, `trainees/${newLog[1]}`);
			resource = record(data);
		}
		const planDetail = path.match(/^\/plans\/([^/]+)$/);
		if (planDetail && resource && !Array.isArray(resource.items)) {
			const type = resource.type ?? '';
			const { data: itemData } = await api<any>(event.fetch, `items?plan_id=${encodeURIComponent(planDetail[1])}&plan_type=${encodeURIComponent(type)}`);
			resource = { ...resource, items: records(itemData) };
		}
		return { path, locale, user, resource, lists, isTemplate: false, error: null };
	} catch (cause) {
		if (isRedirect(cause)) throw cause;
		if (isHttpError(cause)) throw cause;
		if (cause instanceof ApiError && cause.status === 401 && !isPublicPath(path)) {
			throw redirect(303, `/login?next=${encodeURIComponent(path + event.url.search)}`);
		}
		if (cause instanceof ApiError) throw error(cause.status, cause.message);
		throw error(503, 'The service is unavailable.');
	}
};

export const actions: Actions = {
	login: async ({ request, fetch, cookies, url }) => {
		const form = await request.formData();
		try {
			const { data, response } = await api<any>(fetch, 'auth/login', {
				method: 'POST',
				body: JSON.stringify({ identity: String(form.get('identity') ?? '').trim(), password: String(form.get('password') ?? '') })
			});
			const setCookie = response.headers.getSetCookie?.().find((cookie) => /^pb_auth=/i.test(cookie));
			const cookieValue = setCookie?.match(/^pb_auth=([^;]*)/i)?.[1];
			if (cookieValue) cookies.set('pb_auth', decodeURIComponent(cookieValue), {
				path: '/', httpOnly: true, sameSite: 'lax', secure: url.protocol === 'https:', maxAge: 60 * 60 * 24 * 14
			});
			const user = record(data?.user ?? data);
			const next = String(form.get('next') ?? '');
			const safeNext = next.startsWith('/') && !next.startsWith('//') && !next.includes('\\') ? next : '';
			throw redirect(303, safeNext || (user?.role === 'trainee' ? '/user/dashboard' : '/dashboard'));
		} catch (cause) {
			if (isRedirect(cause)) throw cause;
			return fail(cause instanceof ApiError ? cause.status : 503, { error: cause instanceof Error ? cause.message : 'Could not sign in.' });
		}
	},
	logout: async ({ fetch, cookies }) => {
		try { await api(fetch, 'auth/logout', { method: 'POST' }); } catch { /* Always clear the browser session. */ }
		cookies.delete('pb_auth', { path: '/' });
		throw redirect(303, '/login');
	},
	changePassword: async ({ request, fetch, cookies, url }) => {
		const form = await request.formData();
		const values = Object.fromEntries(form.entries());
		if (values.new_password !== values.confirm_password) return fail(400, { error: 'Passwords do not match.' });
		try {
			const { response } = await api(fetch, 'auth/change-password', { method: 'POST', body: JSON.stringify(values) });
			const setCookie = response.headers.getSetCookie?.().find((cookie) => /^pb_auth=/i.test(cookie));
			const cookieValue = setCookie?.match(/^pb_auth=([^;]*)/i)?.[1];
			if (cookieValue) cookies.set('pb_auth', decodeURIComponent(cookieValue), { path: '/', httpOnly: true, sameSite: 'lax', secure: url.protocol === 'https:' });
			throw redirect(303, form.get('role') === 'trainee' ? '/user/dashboard' : '/dashboard');
		} catch (cause) {
			if (isRedirect(cause)) throw cause;
			return fail(cause instanceof ApiError ? cause.status : 503, { error: cause instanceof Error ? cause.message : 'Could not change password.' });
		}
	},
	locale: async ({ request, cookies, url }) => {
		const form = await request.formData();
		const locale = String(form.get('locale') ?? 'en');
		if (['en', 'es', 'tr', 'hy'].includes(locale)) cookies.set('gyme_locale', locale, { path: '/', sameSite: 'lax', maxAge: 60 * 60 * 24 * 365 });
		throw redirect(303, `${url.pathname}${url.search.replace(/([?&])locale=[^&]*&?/, '$1').replace(/[?&]$/, '')}`);
	},
	submit: async ({ request, fetch, url }) => {
		const form = await request.formData();
		const path = (url.pathname.replace(/\/$/, '') || '/').replace(/\/edit$/, '');
		const value = (key: string) => String(form.get(key) ?? '');
		const isDelete = value('intent') === 'delete';
		const numericFields = new Set(['days_per_week', 'seq', 'order', 'sets', 'reps', 'weight', 'rest_seconds', 'height', 'chest', 'waist', 'hip', 'arms', 'bmi', 'bfp', 'bmr', 'tdee', 'lbm', 'whr']);
		const payload: Record<string, any> = {};
		for (const [key, item] of form.entries()) {
			if (key === 'intent' || (item instanceof File && !item.name)) continue;
			if (item instanceof File) payload[key] = item;
			else if (item === '') payload[key] = null;
			else if (key === 'is_template') payload[key] = ['true', 'on', '1', 'yes'].includes(item.toLowerCase());
			else if (numericFields.has(key)) payload[key] = Number(item);
			else payload[key] = item;
		}
		let method = 'POST';
		let endpoint = '';
		let destination = path;
		if (path === '/trainees/new') { endpoint = 'trainees'; destination = '/trainees'; }
		else if (/^\/trainees\/[^/]+$/.test(path)) { const id = path.split('/')[2]; endpoint = `trainees/${id}`; method = isDelete ? 'DELETE' : 'PATCH'; destination = isDelete ? '/trainees' : `/trainees/${id}`; }
		else if (path === '/coaches/new') { endpoint = 'coaches'; destination = '/coaches'; }
		else if (/^\/coaches\/[^/]+$/.test(path)) { const id = path.split('/')[2]; endpoint = `coaches/${id}`; method = isDelete ? 'DELETE' : 'PATCH'; destination = isDelete ? '/coaches' : `/coaches/${id}`; }
		else if (path === '/plans') { endpoint = 'plans'; destination = value('is_template') === 'true' ? '/plans?is_template=true' : '/plans'; }
		else if (path === '/plans/new') { endpoint = 'plans'; destination = value('is_template') === 'true' ? '/plans?is_template=true' : '/plans'; }
		else if (/^\/plans\/[^/]+$/.test(path)) { const id = path.split('/')[2]; endpoint = `plans/${id}`; method = isDelete ? 'DELETE' : 'PATCH'; destination = isDelete ? '/plans' : `/plans/${id}`; }
		else if (/^\/templates\/[^/]+\/apply$/.test(path)) { endpoint = `templates/${path.split('/')[2]}/apply`; destination = '/plans'; }
		else if (path === '/items/new') { endpoint = 'items'; destination = `/plans/${value('plan')}`; }
		else if (/^\/items\/[^/]+$/.test(path)) { const id = path.split('/')[2]; endpoint = `items/${id}?plan_type=${encodeURIComponent(value('plan_type'))}`; method = isDelete ? 'DELETE' : 'PATCH'; destination = `/plans/${value('plan')}`; }
		else if (/^\/trainees\/[^/]+\/progress-log$/.test(path)) { endpoint = `progress-logs`; destination = `/trainees/${path.split('/')[2]}`; }
		else if (/^\/progress-log\/new\/[^/]+$/.test(url.pathname)) { endpoint = 'progress-logs'; payload.trainee = url.pathname.split('/')[3]; destination = `/trainees/${payload.trainee}`; }
		else if (/^\/progress-log\/[^/]+$/.test(path)) { endpoint = `progress-logs/${path.split('/')[2]}`; method = 'PATCH'; destination = payload.trainee ? `/trainees/${payload.trainee}` : '/trainees'; }
		else if (/^\/user\/plans\/[^/]+\/done$/.test(path)) { endpoint = `user/plans/${path.split('/')[3]}/done`; destination = '/user/dashboard'; }
		else if (path === '/profile' || path === '/user/profile') { endpoint = 'auth/profile'; method = 'PATCH'; destination = path; delete payload.email; }
		else return fail(400, { error: 'This action is not available.' });

		try {
			const multipart = [...form.values()].some((item) => item instanceof File && item.name);
			const body = method === 'DELETE' ? undefined : multipart ? form : JSON.stringify(payload);
			const result = await api<any>(fetch, endpoint, { method, body: body as BodyInit | undefined });
			if (path === '/trainees/new') {
				const created = record(result.data);
				if (created?.id) destination = `/progress-log/new/${created.id}`;
			}
			if (/^\/templates\/[^/]+\/apply$/.test(path)) {
				const created = record(result.data);
				if (created?.id) destination = `/plans/${created.id}`;
			}
			throw redirect(303, destination);
		} catch (cause) {
			if (isRedirect(cause)) throw cause;
			return fail(cause instanceof ApiError ? cause.status : 503, { error: cause instanceof Error ? cause.message : 'The change could not be saved.' });
		}
	}
};
