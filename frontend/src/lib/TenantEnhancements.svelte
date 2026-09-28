<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { t } from '$lib/i18n';

  type Locale = 'en' | 'es' | 'tr' | 'hy';
  type TenantData = {
    tenantName?: string;
    tenantLogo?: string;
    tenantTheme?: string;
    brandTheme?: Record<string, unknown>;
    brandColors?: Record<string, unknown>;
    primaryColor?: unknown;
  };

  let { data }: { data: TenantData } = $props();
  let ios = $state(false);
  let standalone = $state(false);
  let showPrompt = $state(false);
  const locale = $derived((($page.data.locale as string) || 'en') as Locale);

  function safeColor(value: unknown): string | null {
    if (typeof value !== 'string' || value.length > 80) return null;
    return /^(#[\da-f]{3,8}|[a-z]+|(?:rgb|hsl|oklch|lab|lch)a?\([\d\s.,%/-]+\))$/i.test(value)
      ? value
      : null;
  }

  function setTenantTheme() {
    const root = document.documentElement;
    for (const [key, value] of Object.entries(data.brandTheme ?? {})) {
      const name = key.replace(/^--/, '').replaceAll('_', '-');
      const color = safeColor(value);
      if (/^[a-z][a-z\d-]*$/i.test(name) && color) root.style.setProperty(`--${name}`, color);
    }

    const colors = data.brandColors ?? {};
    const pumice = safeColor(colors.base_100);
    const obsidian = safeColor(colors.base_content);
    const ember = safeColor(data.primaryColor);
    if (pumice) root.style.setProperty('--pumice', pumice);
    if (obsidian) root.style.setProperty('--obsidian', obsidian);
    if (ember) root.style.setProperty('--ember', ember);
  }

  function addAppleStartupImage() {
    const ratio = window.devicePixelRatio || 1;
    const width = Math.round(window.screen.width * ratio);
    const height = Math.round(window.screen.height * ratio);
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext('2d');
    if (!context) return;

    const background =
      safeColor(data.primaryColor) ?? safeColor(data.brandColors?.base_100) ?? '#e2e2df';
    const foreground = safeColor(data.brandColors?.base_content) ?? '#070607';
    const render = (logo?: HTMLImageElement) => {
      context.fillStyle = background;
      context.fillRect(0, 0, width, height);
      if (logo) {
        const size = Math.round(width / 3);
        context.drawImage(logo, (width - size) / 2, height * 0.25, size, size);
      }
      context.fillStyle = foreground;
      context.textAlign = 'center';
      context.font = `600 ${Math.max(18, Math.round(width * 0.045))}px "DM Sans", sans-serif`;
      context.fillText(data.tenantName || 'Gyme', width / 2, height * 0.67, width * 0.84);
      context.font = `400 ${Math.max(12, Math.round(width * 0.025))}px "DM Sans", sans-serif`;
      context.fillText('•••', width / 2, height * 0.73);

      try {
        let link = document.querySelector<HTMLLinkElement>('[data-gyme-startup-image]');
        if (!link) {
          link = document.createElement('link');
          link.rel = 'apple-touch-startup-image';
          link.dataset.gymeStartupImage = '';
          document.head.append(link);
        }
        link.href = canvas.toDataURL('image/png');
        link.media = `screen and (device-width: ${window.screen.width}px) and (device-height: ${window.screen.height}px) and (-webkit-device-pixel-ratio: ${ratio})`;
      } catch {
        // Cross-origin tenant logos may prevent canvas export; the install flow still works.
      }
    };

    if (!data.tenantLogo) {
      render();
      return;
    }
    const logo = new Image();
    logo.crossOrigin = 'anonymous';
    logo.onload = () => render(logo);
    logo.onerror = () => render();
    logo.src = data.tenantLogo;
  }

  function dismissPrompt() {
    showPrompt = false;
    try {
      localStorage.setItem('ios-install-overlay-dismissed', 'true');
    } catch {
      // Dismiss for this visit when storage is unavailable.
    }
  }

  onMount(() => {
	let savedTheme: string | null = null;
	try {
		savedTheme = localStorage.getItem('gyme-theme');
	} catch {
		// Storage can be disabled in private browsing.
	}
    if (!savedTheme) {
      const tenantTheme = data.tenantTheme === 'custom' ? 'light' : data.tenantTheme;
      if (tenantTheme && /^[a-z][a-z\d-]*$/i.test(tenantTheme)) {
        document.documentElement.dataset.theme = tenantTheme;
      }
    }
    setTenantTheme();

    const agent = navigator.userAgent.toLowerCase();
    ios = /iphone|ipad|ipod/.test(agent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
    standalone =
      (navigator as Navigator & { standalone?: boolean }).standalone === true ||
      window.matchMedia('(display-mode: standalone)').matches;
    if (ios) addAppleStartupImage();
  });

  $effect(() => {
    if (!ios || standalone || $page.url.pathname !== '/login') {
      showPrompt = false;
      return;
    }
    try {
      showPrompt = localStorage.getItem('ios-install-overlay-dismissed') !== 'true';
    } catch {
      showPrompt = true;
    }
  });
</script>

{#if showPrompt && $page.url.pathname === '/login'}
  <div class="fixed inset-0 z-[100] flex items-end justify-center bg-obsidian/70 p-4 sm:items-center" role="presentation">
		<dialog open class="m-0 w-full max-w-md border border-obsidian/15 bg-limestone p-6 text-obsidian" aria-modal="true" aria-labelledby="ios-install-title">
      <div class="mb-5 flex items-start justify-between gap-4">
        <div>
          <h2 id="ios-install-title" class="font-display text-2xl">{t(locale, 'Install the app')}</h2>
          <p class="mt-2 text-sm">{t(locale, 'Add the web app to your home screen.')}</p>
        </div>
        <img class="h-12 w-12 border border-obsidian/15 object-cover" src={data.tenantLogo || '/favicon.svg'} alt="" />
      </div>
      <ol class="space-y-3 text-sm">
        <li class="flex items-center gap-2"><span class="font-display text-lg">1</span>{t(locale, 'Tap the')} <span class="inline-grid h-7 w-7 place-items-center border border-obsidian/20" aria-label={t(locale, 'Share')}>↑</span> {t(locale, 'Share')}</li>
        <li class="flex items-center gap-2"><span class="font-display text-lg">2</span>{t(locale, 'Add to Home Screen')}</li>
        <li class="flex items-center gap-2"><span class="font-display text-lg">3</span>{t(locale, 'Tap Add')}</li>
      </ol>
      <button class="mt-6 min-h-11 w-full bg-ember px-4 font-semibold text-white" type="button" onclick={dismissPrompt}>{t(locale, 'Got it')}</button>
		</dialog>
  </div>
{/if}
