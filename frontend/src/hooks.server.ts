import type { Handle } from '@sveltejs/kit';

const locales = new Set(['en', 'es', 'tr', 'hy']);

export const handle: Handle = async ({ event, resolve }) => {
	const query = event.url.searchParams.get('locale');
	const saved = event.cookies.get('gyme_locale');
	const locale = locales.has(query ?? '') ? query : locales.has(saved ?? '') ? saved : 'en';
	return resolve(event, {
		transformPageChunk: ({ html }) => html.replace('<html lang="en">', `<html lang="${locale}">`)
	});
};
