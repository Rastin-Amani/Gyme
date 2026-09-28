<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { enhance } from '$app/forms';
	import './app.css';
import { t } from '$lib/i18n';
import TenantEnhancements from '$lib/TenantEnhancements.svelte';
	let { children, data } = $props();
	let online = $state(true);
	let dark = $state(false);
	const localeNames: Record<string, string> = { en: 'English', es: 'Español', tr: 'Türkçe', hy: 'Հայերեն' };
	onMount(() => {
		const sync = () => (online = navigator.onLine);
		const saved = localStorage.getItem('gyme-theme');
		dark = saved === 'dark';
		document.documentElement.dataset.theme = dark ? 'dark' : 'light';
		sync();
		window.addEventListener('online', sync);
		window.addEventListener('offline', sync);
		return () => { window.removeEventListener('online', sync); window.removeEventListener('offline', sync); };
	});
	function toggleTheme() {
		dark = !dark;
		document.documentElement.dataset.theme = dark ? 'dark' : 'light';
		localStorage.setItem('gyme-theme', dark ? 'dark' : 'light');
	}
	$effect(() => {
		if (typeof document !== 'undefined') document.documentElement.lang = $page.data.locale ?? 'en';
	});
</script>

<TenantEnhancements {data} />

<svelte:head>
	<title>{data.tenantName} · Coaching, with intention</title>
	<meta name="description" content="Training plans and progress, together." />
	<meta name="apple-mobile-web-app-capable" content="yes" />
</svelte:head>

{#if !$page.url.pathname.startsWith('/login')}
	<div class="frame">
		<header class="topbar">
			<a class="brand" href="/dashboard" aria-label={`${data.tenantName} home`}>
				{#if data.tenantLogo}<img class="brand-logo" src={data.tenantLogo} alt="" />{:else}<span class="brand-mark">G</span>{/if}
				<span>{data.tenantName}</span>
			</a>
			<div class="top-actions">
				<form method="POST" action="?/locale" use:enhance>
					<label class="sr-only" for="locale-select">{t($page.data.locale ?? 'en', 'Change language')}</label>
					<select id="locale-select" name="locale" class="locale-select" value={$page.data.locale ?? 'en'} onchange={(event) => (event.currentTarget.form?.requestSubmit())}>
						{#each Object.entries(localeNames) as [code, label]}<option value={code}>{label}</option>{/each}
					</select>
				</form>
				<button class="icon-button" type="button" onclick={toggleTheme} aria-label={t($page.data.locale ?? 'en', 'Light / dark theme')}>{dark ? '☼' : '◐'}</button>
				{#if $page.data.user}
					<a class="avatar" href={$page.data.user.role === 'trainee' ? '/user/profile' : '/profile'} aria-label={t($page.data.locale ?? 'en', 'Open profile')}>{($page.data.user.first_name ?? 'G').slice(0, 1)}</a>
				{/if}
			</div>
		</header>
		{#if $page.data.user}
			<nav class="nav" aria-label="Main navigation">
				{#if $page.data.user.role === 'trainee'}
					<a class:active={$page.url.pathname === '/user/dashboard'} href="/user/dashboard">{t($page.data.locale ?? 'en', 'Today')}</a>
					<a class:active={$page.url.pathname.startsWith('/user/plans')} href="/user/plans">{t($page.data.locale ?? 'en', 'Plans')}</a>
					<a class:active={$page.url.pathname.startsWith('/user/profile')} href="/user/profile">{t($page.data.locale ?? 'en', 'Profile')}</a>
				{:else}
					<a class:active={$page.url.pathname === '/dashboard'} href="/dashboard">{t($page.data.locale ?? 'en', 'Dashboard')}</a>
					<a class:active={$page.url.pathname.startsWith('/plans') || $page.url.pathname.startsWith('/templates')} href="/plans">{t($page.data.locale ?? 'en', 'Plans')}</a>
					<a class:active={$page.url.pathname.startsWith('/trainees')} href="/trainees">{t($page.data.locale ?? 'en', 'Trainees')}</a>
					{#if $page.data.user.role === 'owner'}<a class:active={$page.url.pathname.startsWith('/coaches')} href="/coaches">{t($page.data.locale ?? 'en', 'Coaches')}</a>{/if}
					<a class:active={$page.url.pathname.startsWith('/profile')} href="/profile">{t($page.data.locale ?? 'en', 'Profile')}</a>
				{/if}
				<form method="POST" action="?/logout" use:enhance class="signout-form"><button class="nav-logout" type="submit">{t($page.data.locale ?? 'en', 'Sign out')}</button></form>
			</nav>
		{/if}
		{#if !online}<div class="offline" role="status">You’re offline. Changes may not save.</div>{/if}
		<main id="main-content">{@render children()}</main>
		<footer class="foot"><span>GYME / COACHING SYSTEM</span><span>MOVE WITH INTENTION</span></footer>
	</div>
{:else}
	<main id="main-content" class="auth-frame">
		<div class="auth-tools"><form method="POST" action="?/locale" use:enhance><label class="sr-only" for="auth-locale">{t($page.data.locale ?? 'en', 'Change language')}</label><select id="auth-locale" name="locale" value={$page.data.locale ?? 'en'} onchange={(event) => event.currentTarget.form?.requestSubmit()}>{#each Object.entries(localeNames) as [code, label]}<option value={code}>{label}</option>{/each}</select></form><button class="icon-button" type="button" onclick={toggleTheme} aria-label={t($page.data.locale ?? 'en', 'Light / dark theme')}>{dark ? '☼' : '◐'}</button></div>
		{@render children()}
	</main>
{/if}
