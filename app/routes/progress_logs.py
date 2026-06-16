from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from ..templates import templates
from app.utils import hx_toast
from app.services.trainee import get_trainee_by_id, update_trainee
from app.services.progress_logs import create_progress_log

router = APIRouter(
    tags=["Progress Logs"]
)

@router.get("/progress-log/new/{trainee_id}")
async def new_progress_log_form(request: Request, trainee_id: str):
    pb = request.state.pb
    tenant = request.state.tenant
    user = request.state.user

    # Only coaches/owners can create logs
    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")
    
    try:
        trainee = get_trainee_by_id(pb, tenant.id, trainee_id)
    except Exception:
        return RedirectResponse(url="/trainees")

    return templates.TemplateResponse(
        request=request,
        name="forms/progress_logs.html",
        context={
            "title": "ثبت ارزیابی اولیه",
            "tenant": tenant,
            "user": user,
            "trainee": trainee
        }
    )

@router.post("/trainees/{trainee_id}/progress-log")
async def save_progress_log(
    request: Request,
    trainee_id: str,
    height: float = Form(...),
    weight: float = Form(...),
    chest: float = Form(None),
    waist: float = Form(...),
    hip: float = Form(None),
    arms: float = Form(None),
    notes: str = Form(None),
    # 🟢 Calculated fields from the hidden inputs
    bmi: float = Form(None),
    bfp: float = Form(None),
    bmr: float = Form(None),
    tdee: float = Form(None),
    lbm: float = Form(None),
    whr: float = Form(None),
):
    pb = request.state.pb
    tenant_id = request.state.tenant.id

    log_data = {
        "tenant": tenant_id,
        "trainee": trainee_id,
        "height": str(height), # Assuming DB wants string or number based on schema
        "weight": weight,
        "chest": chest,
        "waist": waist,
        "hip": hip,
        "arms": arms,
        "notes": notes,
        "bmi": bmi,
        "bfp": bfp,
        "bmr": bmr,
        "tdee": tdee,
        "lbm": lbm,
        "whr": whr
    }

    try:
        # 1. Save the new log
        create_progress_log(pb, log_data)
        
        # 2. Update the Trainee's main profile with their latest height and weight!
        update_trainee(pb, trainee_id, {"height": height, "weight": weight})

        headers = hx_toast("ارزیابی با موفقیت ثبت شد!", "success")
        headers["HX-Redirect"] = f"/trainees/{trainee_id}" # Take coach to trainee profile
        return HTMLResponse(content="", headers=headers)
        
    except Exception as e:
        print(f"Error creating progress log: {e}")
        headers = hx_toast("خطا در ثبت اطلاعات ارزیابی!", "error")
        return HTMLResponse(content="", headers=headers, status_code=400)