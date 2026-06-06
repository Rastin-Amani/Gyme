from urllib import request

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()

@router.get("/manifest.json", response_class=JSONResponse)
async def dynamic_manifest(request: Request):
    pb = request.state.pb
    pb_base_url = pb.base_url.rstrip("/")
    tenant = getattr(request.state, 'tenant', None)
    tenant_name = getattr(tenant, 'name', 'Gyme') if tenant else 'Gyme'
    
    # 1. Check if the tenant has uploaded a logo 🖼️
    logo_filename = getattr(tenant, 'logo', None) if tenant else None
    
    if tenant and logo_filename:
        collection_id = getattr(tenant, 'collection_id', 'tenants')
        tenant_id = getattr(tenant, 'id', '')
        
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
            {
                "src": icon_192,
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": icon_512,
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ]
    }

    return manifest

from fastapi.responses import RedirectResponse

@router.get("/favicon.ico", include_in_schema=False)
async def dynamic_favicon(request: Request):
    # Grab the pb instance to get its base URL dynamically
    pb = request.state.pb
    pb_base_url = pb.base_url.rstrip("/") 
    
    tenant = getattr(request.state, 'tenant', None)
    logo_filename = getattr(tenant, 'logo', None) if tenant else None
    
    if tenant and logo_filename:
        collection_id = getattr(tenant, 'collection_id', 'tenants')
        tenant_id = getattr(tenant, 'id', '')
        
        # 🟢 Construct the ABSOLUTE URL and ask PocketBase for a tiny 32x32 thumbnail
        favicon_url = f"{pb_base_url}/api/files/{collection_id}/{tenant_id}/{logo_filename}?thumb=32x32f"
        
        # Instantly redirect the browser to the PocketBase image
        return RedirectResponse(url=favicon_url)
        
    # 🟢 Fallback to your default Gyme favicon if the gym hasn't uploaded a logo
    return RedirectResponse(url="/static/icons/favicon.ico")