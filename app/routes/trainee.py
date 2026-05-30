from fastapi import APIRouter, Request, Form
from app.services.trainee import create_trainee, list_trainees, get_trainee_by_id, update_trainee
from app.services.auth import create_user, update_user
from ..templates import templates
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse
from app.services.plan import get_plans_by_trainee


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
    tenant = request.state.tenant
    user = request.state.user
    trainee_data = get_trainee_by_id(pb, tenant.id, id)
    tenant_name = request.state.tenant
    plans = get_plans_by_trainee(pb, tenant.id, id)

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
        "plans": plans
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
    email: str = Form(...), 
    phone: str = Form(None), # 🟢 Still captured from the HTML form
    gender: str = Form(None),
    birthdate: str = Form(None),
    height: int = Form(None),
    weight: int = Form(None),
    notes: str = Form(None),
):
    pb = request.state.pb
    tenant_id = request.state.tenant.id 
    
    # --- STEP 1: Create the Auth User ---
    user_result = create_user(
        pb=pb,
        tenant_id=tenant_id,
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone=phone, # 🟢 Handed off to the users collection
        role="trainee"
    )
    
    if not user_result["ok"]:
        return HTMLResponse(
            content=f"<div class='alert alert-error'>{user_result['error']}</div>", 
            status_code=400
        )
        
    new_user = user_result["user"]

    # --- STEP 2: Create the Trainee Profile ---
    trainee_data = {
        "tenant": tenant_id,
        "user": new_user.id,
        "status": "active",
        "gender": gender,
        "birthdate": birthdate,
        "height": height,
        "weight": weight,
        "notes": notes,
    }

    try:
        # Assumes you have your create_trainee function imported
        create_trainee(pb, tenant_id, trainee_data)
    except Exception as e:
        # Cleanup: Delete the auth user if the trainee profile fails to create
        pb.collection("users").delete(new_user.id)
        return HTMLResponse(
            content="<div class='alert alert-error'>خطا در ایجاد پروفایل شاگرد!</div>", 
            status_code=400
        )
    
    # --- STEP 3: Success! Redirect back to the list ---
    return HTMLResponse(headers={"HX-Redirect": "/trainees"})

@router.post("/trainees/{id}")
async def trainee_update(
    request: Request,
    id: str,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...), # Required for Auth User
    phone: str = Form(None),
    gender: str = Form(None),
    birthdate: str = Form(None),
    height: int = Form(None),
    weight: int = Form(None),
    notes: str = Form(None),
):
    pb = request.state.pb
    tenant_id = request.state.tenant.id 
    
    # --- STEP 1: Fetch existing trainee to get the User ID ---
    try:
        # Reusing your existing service to get the trainee record
        trainee = get_trainee_by_id(pb, tenant_id, id)
        user_id = trainee.user
    except Exception:
        return HTMLResponse(
            content="<div class='alert alert-error'>Trainee not found!</div>", 
            status_code=404
        )

    # --- STEP 2: Update the Auth User ---
    user_data = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone
    }
    
    try:
        # Using the new service you just created
        update_user(pb, user_id, user_data)
    except Exception as e:
        print(f"Failed to update user: {e}")
        return HTMLResponse(
            content="<div class='alert alert-error'>Failed to update user! (Email might already be in use)</div>", 
            status_code=400
        )

    # --- STEP 3: Update the Trainee Profile ---
    # Notice we removed name, email, and phone from this payload!
    trainee_data = {
        "gender": gender,
        "birthdate": birthdate,
        "height": height,
        "weight": weight,
        "notes": notes,
    }

    try:
        update_trainee(pb, id, trainee_data)
    except Exception as e:
        print(f"Failed to update trainee: {e}")
        return HTMLResponse(
            content="<div class='alert alert-error'>Failed to update trainee profile!</div>", 
            status_code=400
        )
    
    # --- STEP 4: Success! Redirect back to the list ---
    return HTMLResponse(headers={"HX-Redirect": "/trainees"})