from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from app.services.dashboard import get_owner_dashboard_stats
from ..templates import templates

router = APIRouter(tags=["Dashboard"])

@router.get("/dashboard")
async def owner_dashboard(request: Request, timeframe: str = "all"):
    pb = request.state.pb
    tenant = request.state.tenant
    user = request.state.user
    tenant_id = request.state.tenant.id

    # Fetch the stats based on the selected timeframe
    stats = get_owner_dashboard_stats(pb, tenant_id, timeframe)

    context = {
        "title": "داشبورد مدیریت",
        "stats": stats,
        "timeframe": timeframe,
        "tenant": tenant,  
        "user": user
    }

    # HTMX Magic: If the request comes from the timeframe dropdown, 
    # only return the stats HTML fragment, not the whole page!
    if request.headers.get("hx-target") == "stats-container":
        return templates.TemplateResponse(
            request=request,
            name="components/dashboard_stats.html",
            context=context
        )

    # Standard full page load
    return templates.TemplateResponse(
        request=request,
        name="pages/owner/dashboard.html",
        context=context
    )