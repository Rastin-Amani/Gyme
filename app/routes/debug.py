from fastapi import APIRouter, Request

router = APIRouter(prefix="/debug", tags=["debug"])

@router.get("/tenant")
def debug_tenant(request: Request):
    tenant = getattr(request.state, "tenant", None)

    if not tenant:
        return {"tenant": None}

    return {
        "id": tenant.id,
        "domain": tenant.domain,
        "name": tenant.name,
    }
