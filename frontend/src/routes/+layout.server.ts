interface ManifestData {
  name?: string;
  icons?: Array<{ src?: string }>;
}

interface TenantBranding {
  name?: string;
  logo_url?: string | null;
  theme?: string;
  brand_theme?: Record<string, string>;
  brand_colors?: Record<string, string>;
  primary_color?: string | null;
}

export async function load({ fetch }) {
  const [manifest, branding] = await Promise.all([
    fetch('/manifest.json').then((response) => response.ok ? (response.json() as Promise<ManifestData>) : ({} as ManifestData)).catch(() => ({} as ManifestData)),
    fetch('/api/v1/tenant/branding').then((response) => response.ok ? (response.json() as Promise<TenantBranding>) : ({} as TenantBranding)).catch(() => ({} as TenantBranding))
  ]);

  return {
    tenantName: branding.name || manifest.name || 'Gyme',
    tenantLogo: branding.logo_url || manifest.icons?.[0]?.src || '/favicon.svg',
    tenantTheme: branding.theme || 'gyme',
    brandTheme: branding.brand_theme || {},
    brandColors: branding.brand_colors || {},
    primaryColor: branding.primary_color || null
  };
}
