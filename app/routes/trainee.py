from fastapi import APIRouter, Request, Form
from app.services.trainee import create_trainee, list_trainees, get_trainee_by_id, update_trainee
from ..templates import templates
from fastapi.responses import HTMLResponse

router = APIRouter()

# Get Requests
@router.get("/trainees")
async def trainee_new_form (request: Request):
    pb = request.state.pb
    tenant = request.state.tenant.id
    trainees = list_trainees(pb, tenant)
    tenant_name = request.state.tenant
    return templates.TemplateResponse(
        request=request,
        name="pages/trainees.html",
        context={
        "title" : "لیست شاگردان",
        "tenant": tenant_name,
        "trainees": trainees.items,
        }
    )

@router.get("/trainees/new")
async def trainees_list (request: Request):
    # This returns just the form fragment for HTMX or a full page
    tenant = request.state.tenant
    return templates.TemplateResponse(
        request=request,
        name="forms/trainees_form.html",
        context={
        "title" : "ثبت شاگرد جدید",
        "tenant": tenant,
        "trainee": None,

        }
    )

@router.get("/trainees/{id}")
async def show_trainee_detail (request: Request, id: str):
    pb = request.state.pb
    tenant = request.state.tenant.id
    trainee_data = get_trainee_by_id(pb, tenant, id)
    tenant_name = request.state.tenant
    return templates.TemplateResponse(
        request=request,
        name="pages/trainee_detail.html",
        context={
        "title" : "اطلاعات شاگرد",
        "tenant": tenant_name,
        "trainee": trainee_data,
        }
    )


@router.get("/trainees/{id}/edit")
async def trainee_edit_form (request: Request, id: str):
    pb = request.state.pb
    tenant = request.state.tenant.id
    trainee_data = get_trainee_by_id(pb, tenant, id)
    tenant_name = request.state.tenant
    return templates.TemplateResponse(
        request=request,
        name="forms/trainees_form.html",
        context={
        "title" : "ویرایش شاگرد",
        "tenant": tenant_name,
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
