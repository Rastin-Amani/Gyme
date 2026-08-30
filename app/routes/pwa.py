from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

router = APIRouter()

# Path to SW file relative to project root
SW_PATH = Path(__file__).resolve().parent.parent / "static" / "sw.js"


@router.get("/sw.js", include_in_schema=False)
def service_worker():
    # Lazy import avoids circular import: main.py imports pwa before APP_VERSION is defined
    from app.main import APP_VERSION

    content = SW_PATH.read_text(encoding="utf-8")
    # Inject app version into CACHE_VERSION so caches auto-purge on deploy
    content = content.replace("__CACHE_VERSION__", APP_VERSION)
    return Response(
        content=content,
        media_type="application/javascript",
        headers={
            "Service-Worker-Allowed": "/",
            "Cache-Control": "no-cache",
        },
    )


@router.get("/offline/", include_in_schema=False, response_class=HTMLResponse)
def offline_page():
    return """<!doctype html>
<html dir="rtl">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>قطع ارتباط</title>
    <style>
      * { margin: 0; padding: 0; box-sizing: border-box; }
      body {
        font-family: system-ui, -apple-system, sans-serif;
        background: #1d232a;
        color: #ffffff;
        min-height: 100dvh;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 2rem;
        text-align: center;
      }
      .icon {
        width: 80px; height: 80px; border-radius: 50%;
        background: #ef444422;
        display: flex; align-items: center; justify-content: center;
        margin-bottom: 1.5rem;
      }
      .icon svg { width: 40px; height: 40px; stroke: #ef4444; fill: none; stroke-width: 1.5; }
      h1 { font-size: 1.25rem; font-weight: 700; margin-bottom: 0.75rem; }
      p { color: #9ca3af; line-height: 1.6; margin-bottom: 2rem; max-width: 300px; }
      .btn {
        display: inline-flex; align-items: center; gap: 0.5rem;
        padding: 0.75rem 2rem; background: #2a7eff; color: #fff;
        border: none; border-radius: 999px; font-size: 0.875rem; font-weight: 600;
        cursor: pointer; transition: opacity 0.2s;
      }
      .btn:hover { opacity: 0.85; }
      .btn:active { opacity: 0.7; }
    </style>
  </head>
  <body>
    <div class="icon">
      <svg viewBox="0 0 24 24" stroke-linecap="round" stroke-linejoin="round">
        <path d="M18.364 5.636a9 9 0 0 1 0 12.728m-2.829-2.829a5 5 0 0 0 0-7.07m-4.243 4.243a1 1 0 0 1 0-1.414" />
        <path d="M3 3l18 18" />
      </svg>
    </div>
    <h1>شما آفلاین هستید</h1>
    <p>صفحه‌هایی که قبلاً دیده‌اید هنوز در دسترس هستند.<br />پس از اتصال به اینترنت، دوباره امتحان کنید.</p>
    <button class="btn" onclick="window.location.reload()">تلاش مجدد</button>
  </body>
</html>"""


@router.get("/manifest.json", response_class=JSONResponse)
def dynamic_manifest(request: Request):
    pb = request.state.pb
    pb_base_url = pb.base_url.rstrip("/")
    tenant = getattr(request.state, "tenant", None)
    tenant_name = getattr(tenant, "name", "Gyme") if tenant else "Gyme"

    # 1. Check if the tenant has uploaded a logo 🖼️
    logo_filename = getattr(tenant, "logo", None) if tenant else None

    if tenant and logo_filename:
        collection_id = getattr(tenant, "collection_id", "tenants")
        tenant_id = getattr(tenant, "id", "")

        # Construct the native PocketBase file URL
        base_icon_url = f"{pb_base_url}/api/files/{collection_id}/{tenant_id}/{logo_filename}"

        # PRO-TIP: Use PocketBase's built-in thumb generator for exact PWA sizing!
        icon_192 = f"{base_icon_url}?thumb=192x192f"
        icon_512 = f"{base_icon_url}?thumb=512x512f"
    else:
        # 2. Fallback to your default Gyme icon if the tenant has no logo
        icon_192 = "/static/icons/icon-192x192.png"
        icon_512 = "/static/icons/icon-512x512.png"

    # 3. Build the Manifest
    manifest = {
        "name": f"{tenant_name}",
        "short_name": tenant_name,
        "description": f"اپلیکیشن اختصاصی {tenant_name}",
        "start_url": "/login",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#1d232a",
        "theme_color": "#1d232a",
        "icons": [
            {"src": icon_192, "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
            {"src": icon_512, "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
    }

    return manifest


from fastapi.responses import RedirectResponse


@router.get("/favicon.ico", include_in_schema=False)
def dynamic_favicon(request: Request):
    # Grab the pb instance to get its base URL dynamically
    pb = request.state.pb
    pb_base_url = pb.base_url.rstrip("/")

    tenant = getattr(request.state, "tenant", None)
    logo_filename = getattr(tenant, "logo", None) if tenant else None

    if tenant and logo_filename:
        collection_id = getattr(tenant, "collection_id", "tenants")
        tenant_id = getattr(tenant, "id", "")

        # 🟢 Construct the ABSOLUTE URL and ask PocketBase for a tiny 32x32 thumbnail
        favicon_url = (
            f"{pb_base_url}/api/files/{collection_id}/{tenant_id}/{logo_filename}?thumb=32x32f"
        )

        # Instantly redirect the browser to the PocketBase image
        return RedirectResponse(url=favicon_url)

    # 🟢 Fallback to your default Gyme favicon if the gym hasn't uploaded a logo
    return RedirectResponse(url="/static/icons/favicon.ico")
