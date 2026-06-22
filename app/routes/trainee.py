from fastapi import APIRouter, Request, Form
from app.services.trainee import create_trainee, list_trainees, get_trainee_by_id, update_trainee
from app.services.auth import create_user, update_user
from ..templates import templates
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse
from app.services.plan import get_plans_by_trainee
from app.services.progress_logs import get_progress_logs_by_trainee


router = APIRouter(
    tags=["Trainees Management"]
)

# Get Requests
@router.get("/trainees")
async def trainees_list(request: Request):
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
            "title": "لیست شاگردان",
            "tenant": tenant_name,
            "user": user,
            "trainees": trainees.items,
        }
    )


@router.get("/trainees/search")
async def search_trainees(request: Request, query: str = ""):
    """Search trainees by name, phone, or email"""
    pb = request.state.pb
    tenant = request.state.tenant.id
    
    trainees = list_trainees(pb, tenant, query=query)
    
    return templates.TemplateResponse(
        request=request,
        name="pages/owner/trainee/trainees.html",
        context={
            "title": "لیست شاگردان",
            "tenant": request.state.tenant,
            "user": request.state.user,
            "trainees": trainees.items,
            "is_search_result": True,
            "search_query": query,
            "show_empty_state": len(trainees.items) == 0 and len(query) > 0,
            "empty_message": "هیچ شاگردی با این مشخصات پیدا نشد"
        }
    )


@router.get("/trainees/filter")
async def filter_trainees(
    request: Request,
    gender: str = None,
    status: str = None,
    min_birthdate: str = None,
    max_birthdate: str = None
):
    """Filter trainees by criteria"""
    pb = request.state.pb
    tenant = request.state.tenant.id
    
    trainees = list_trainees(
        pb,
        tenant,
        gender=gender,
        status=status,
        min_birthdate=min_birthdate,
        max_birthdate=max_birthdate
    )
    
    return templates.TemplateResponse(
        request=request,
        name="pages/owner/trainee/trainees.html",
        context={
            "title": "لیست شاگردان",
            "tenant": request.state.tenant,
            "user": request.state.user,
            "trainees": trainees.items,
            "is_search_result": True,
            "search_query": request.query_params.get("query", ""),
            "filter_params": {
                "gender": gender,
                "status": status,
                "min_birthdate": min_birthdate,
                "max_birthdate": max_birthdate
            },
            "show_empty_state": len(trainees.items) == 0,
            "empty_message": "هیچ شاگردی با این فیلتر پیدا نشد"
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
    progress_logs = get_progress_logs_by_trainee(pb, tenant.id, id)

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
        "plans": plans,
        "progress_logs": progress_logs
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
@router.post("/trainees/new")
async def trainee_create(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...), 
    phone: str = Form(None), 
    gender: str = Form(None),
    birthdate: str = Form(None),
    status: str = Form("active"),         # 🟢 Added Status
    training_history: str = Form(None),   
    steroid_history: str = Form(None),    
    supplement_history: str = Form(None), 
    notes: str = Form(None),
):
    pb = getattr(request.state, 'pb', None)
    tenant_id = getattr(request.state, 'tenant', None).id 
    
    # --- STEP 1: Create the Auth User ---
    user_result = create_user(
        pb=pb,
        tenant_id=tenant_id,
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        role="trainee",

    )
    
    if not user_result["ok"]:
        return HTMLResponse(
            content=f"<div class='alert alert-error alert-soft'>{user_result['error']}</div>", 
            status_code=400
        )
        
    new_user = user_result["user"]

    # --- STEP 2: Create the Trainee Profile ---
    trainee_data = {
        "tenant": tenant_id,
        "user": new_user.id,
        "status": status,
        "gender": gender,
        "birthdate": birthdate,
        "training_history": training_history,     
        "steroid_history": steroid_history,       
        "supplement_history": supplement_history, 
        "notes": notes,
    }

    try:
        created_trainee = create_trainee(pb, tenant_id, trainee_data)
        new_trainee_id = created_trainee.id
    except Exception as e:
        # Cleanup: Delete the auth user if the trainee profile fails to create
        pb.collection("users").delete(new_user.id)
        return HTMLResponse(
            content="<div class='alert alert-error alert-soft'>خطا در ایجاد پروفایل شاگرد!</div>", 
            status_code=400
        )
    
    # 🟢 Redirect instantly to the progress log form!
    return HTMLResponse(headers={"HX-Redirect": f"/progress-log/new/{new_trainee_id}"})


@router.post("/trainees/{id}")
async def trainee_update(
    request: Request,
    id: str,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(None),
    gender: str = Form(None),
    birthdate: str = Form(None),
    status: str = Form(None),             # 🟢 Added Status
    training_history: str = Form(None),   
    steroid_history: str = Form(None),    
    supplement_history: str = Form(None), 
    notes: str = Form(None),
):
    pb = getattr(request.state, 'pb', None)
    tenant_id = getattr(request.state, 'tenant', None).id 
    
    # --- STEP 1: Fetch existing trainee ---
    try:
        trainee = get_trainee_by_id(pb, tenant_id, id)
        user_id = trainee.user
    except Exception:
        return HTMLResponse(
            content="<div class='alert alert-error alert-soft'>Trainee not found!</div>", 
            status_code=404
        )

    # --- STEP 2: Update Auth User ---
    user_data = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone
    }
    
    try:
        update_user(pb, user_id, user_data)
    except Exception as e:
        print(f"Failed to update user: {e}")
        return HTMLResponse(
            content="<div class='alert alert-error alert-soft'>Failed to update user!</div>", 
            status_code=400
        )

    # --- STEP 3: Update Trainee Profile ---
    trainee_data = {
        "gender": gender,
        "birthdate": birthdate,
        "status": status,
        "training_history": training_history,     
        "steroid_history": steroid_history,       
        "supplement_history": supplement_history, 
        "notes": notes,
    }

    try:
        update_trainee(pb, id, trainee_data)
    except Exception as e:
        print(f"Failed to update trainee: {e}")
        return HTMLResponse(
            content="<div class='alert alert-error alert-soft'>Failed to update trainee profile!</div>", 
            status_code=400
        )
    
    # 🟢 Redirect back to the trainee details page
    return HTMLResponse(headers={"HX-Redirect": f"/trainees/{id}"})