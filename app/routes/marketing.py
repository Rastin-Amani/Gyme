from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from app.utils import hx_toast # Using your awesome toast utility!
from ..templates import templates

router = APIRouter(
    tags=["Marketing"]
)

@router.get("/")
async def slash(request: Request):
    tenant = request.state.tenant
    return templates.TemplateResponse(
        request=request,
        name="pages/marketing/slash.html",
        context={
            "title": "اپلیکیشن اختصاصی باشگاه شما", 
            "tenant": tenant
            }
    )

@router.post("/lead/submit")
async def submit_lead(
    request: Request, 
    name: str = Form(...), 
    phone: str = Form(...), 
    position: str = Form(...),
    coaches_count: str = Form(...),
    trainees_count: str = Form(...),
    gym_name: str = Form(None),
    note: str = Form(None)
):
    pb = getattr(request.state, 'pb', None)
    
    try:
        payload = {
            "name": name,
            "phone": phone,
            "position": position,
            "coaches_count": coaches_count,
            "trainees_count": trainees_count,
            "gym_name": gym_name,
            "note": note
        }
        
        pb.collection('leads').create(payload)
        
        headers = hx_toast(f"ممنون {name}! تا ۲۴ ساعت آتی با شما تماس می‌گیریم.", "success")
        
        # 🟢 FIXED: Swap the header key so it fires immediately without waiting for a DOM swap!
        trigger_data = headers.pop("HX-Trigger-After-Swap")
        headers["HX-Trigger"] = trigger_data
        
        return HTMLResponse(status_code=204, headers=headers)
        
    except Exception as e:
        print(f"Error submitting lead: {e}")
        headers = hx_toast("مشکلی پیش اومد. لطفا دوباره تلاش کنید.", "error")
        
        # We do the same here just to be safe, since the form has hx-swap="none"
        trigger_data = headers.pop("HX-Trigger-After-Swap", None)
        if trigger_data:
            headers["HX-Trigger"] = trigger_data
            
        return HTMLResponse(status_code=200, headers=headers)