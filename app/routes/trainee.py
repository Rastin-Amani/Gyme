from fastapi import APIRouter, Request, Form
from app.services.trainee import create_trainee, list_trainees, get_trainee_by_id, update_trainee
from ..templates import templates
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse


router = APIRouter(
    tags=["Trainees Management"]
)
# Get Requests
@router.get("/trainees")
async def trainees_list (request: Request):
    pb = request.state.pb
    tenant = request.state.tenant.id
    user = request.state.user
    trainees = list_trainees(pb, tenant)
    tenant_name = request.state.tenant

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")
    
    return templates.TemplateResponse(
        request=request,
        name="pages/owner/trainee/trainees.html",
        context={
        "title" : "لیست شاگردان",
        "tenant": tenant_name,
        "user": user,
        "trainees": trainees.items,
        }
    )

@router.get("/trainees/new")
async def trainees_new_form (request: Request):
    user = request.state.user
    tenant = request.state.tenant

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")
    
    return templates.TemplateResponse(
        request=request,
        name="forms/trainees_form.html",
        context={
        "title" : "ثبت شاگرد جدید",
        "tenant": tenant,
        "user": user,
        "trainee": None,

        }
    )

@router.get("/trainees/{id}")
async def show_trainee_detail (request: Request, id: str):
    pb = request.state.pb
    tenant = request.state.tenant.id
    user = request.state.user
    trainee_data = get_trainee_by_id(pb, tenant, id)
    tenant_name = request.state.tenant

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")
    
    return templates.TemplateResponse(
        request=request,
        name="pages/owner/trainee/trainee_detail.html",
        context={
        "title" : "اطلاعات شاگرد",
        "tenant": tenant_name,
        "user": user,
        "trainee": trainee_data,
        }
    )


@router.get("/trainees/{id}/edit")
async def trainee_edit_form (request: Request, id: str):
    pb = request.state.pb
    tenant = request.state.tenant.id
    user = request.state.user
    trainee_data = get_trainee_by_id(pb, tenant, id)
    tenant_name = request.state.tenant

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")
    
    return templates.TemplateResponse(
        request=request,
        name="forms/trainees_form.html",
        context={
        "title" : "ویرایش شاگرد",
        "tenant": tenant_name,
        "user": user,
        "trainee": trainee_data,
        }
    )




# Post Requests
@router.post("/trainees")
async def trainee_create(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(None),
    phone: str = Form(None),
    gender: str = Form(None),
    birthdate: str = Form(None),
    height: int = Form(None),
    weight: int = Form(None),
    notes: str = Form(None),

):
    pb = request.state.pb
    tenant = request.state.tenant.id # Passing the ID string
    
    data = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        "status": "active",
        "gender": gender,
        "birthdate": birthdate,
        "height": height,
        "weight": weight,
        "notes": notes,
    }

    # Use your functional service
    create_trainee(pb, tenant, data)
    
    # After creation, HTMX can redirect the whole page back to the list
    # or just return the updated list fragment.
    return HTMLResponse(headers={"HX-Redirect": "/trainees"})

@router.post("/trainees/{id}")
async def trainee_update(
    request: Request,
    id: str,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(None),
    phone: str = Form(None),
    gender: str = Form(None),
    birthdate: str = Form(None),
    height: int = Form(None),
    weight: int = Form(None),
    notes: str = Form(None),

):
    pb = request.state.pb
    tenant = request.state.tenant.id # Passing the ID string
    
    data = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        "status": "active",
        "gender": gender,
        "birthdate": birthdate,
        "height": height,
        "weight": weight,
        "notes": notes,
    }

    # Use your functional service
    update_trainee(pb, id, data)
    
    # After creation, HTMX can redirect the whole page back to the list
    # or just return the updated list fragment.
    return HTMLResponse(headers={"HX-Redirect": "/trainees"})
