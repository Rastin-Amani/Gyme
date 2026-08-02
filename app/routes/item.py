from fastapi import APIRouter, Request, Form, Query
import json
from app.services.item import list_items, get_item_by_id, create_item, update_item
from ..templates import templates
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse
import pandas as pd

router = APIRouter(tags=["items Management"])

df = pd.read_csv("data/Persian_Fitness_Exercises_Dataset.csv")
EXERCISE_NAMES = df["نام حرکت (Exercise Name)"].dropna().unique().tolist()

df = pd.read_csv("data/Persian_Diet_Foods_Dataset.csv")
FOOD_NAMES = df["نام غذا/ماده (Persian Name)"].dropna().unique().tolist()


# Get Requests
@router.get("/items/new")
async def item_edit_form(request: Request, plan_type: str = Query(...), plan_id: str = Query(...)):
    tenant = request.state.tenant.id
    collection_name = f"{plan_type}_items"
    user = request.state.user

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")

    return templates.TemplateResponse(
        request=request,
        name="modals/items_form.html",
        context={
            "title": "ویرایش آیتم",
            "tenant": tenant,
            "plan_type": plan_type,
            "plan_id": plan_id,
            "collection_name": collection_name,
            "item": None,
            "exercise_names": EXERCISE_NAMES,
            "food_names": FOOD_NAMES,
        },
    )


@router.get("/items/{id}/edit")
async def item_edit_form(request: Request, id: str, plan_type: str = Query(...)):
    pb = request.state.pb
    tenant = request.state.tenant.id
    user = request.state.user
    collection_name = f"{plan_type}_items"
    item = get_item_by_id(pb, tenant, collection_name, id)
    tenant_name = request.state.tenant

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")

    return templates.TemplateResponse(
        request=request,
        name="modals/items_form.html",
        context={
            "title": "ویرایش آیتم",
            "tenant": tenant_name,
            "item": item,
            "plan_type": plan_type,
            "collection_name": collection_name,
            "exercise_names": EXERCISE_NAMES,
            "food_names": FOOD_NAMES,
        },
    )


# Delete requests
@router.delete("/items/{id}")
async def item_delete(request: Request, id: str, plan_type: str = Query(...)):
    pb = request.state.pb
    tenant = request.state.tenant.id
    collection_name = f"{plan_type}_items"

    try:
        delete_item(pb, id, collection_name)
        
        # 🟢 SUCCESS: Close modal, refresh the list, and show success toast!
        trigger_data = {
            "closeModal": True,
            "refreshList": True,
            "show-toast": {"message": "آیتم با موفقیت حذف شد.", "type": "success"},
        }
        return HTMLResponse(status_code=204, headers={"HX-Trigger": json.dumps(trigger_data)})

    except Exception as e:
        from structlog import get_logger

        logger = get_logger(__name__)
        logger.error("item.delete_failed", error=str(e), item_id=id, plan_type=plan_type)
        # 🔴 ERROR: Keep modal open and show error toast!
        trigger_data = {
            "show-toast": {"message": "مشکلی پیش آمد. لطفا دوباره تلاش کنید.", "type": "error"}
        }
        return HTMLResponse(status_code=204, headers={"HX-Trigger": json.dumps(trigger_data)})


# Confirm delete modal
@router.get("/items/{id}/confirm-delete")
async def item_confirm_delete(request: Request, id: str, plan_type: str = Query(...)):
    return templates.TemplateResponse(
        "modals/confirm_delete.html",
        {
            "request": request,
            "title": "حذف آیتم",
            "delete_url": f"/items/{id}?plan_type={plan_type}",
        },
    )


# Post requests
@router.post("/items")
async def item_create(
    request: Request,
    plan_type: str = Form(...),
    plan: str = Form(...),
    item_name: str = Form(None),  # Training
    seq: int = Form(None),  # Training (Day)
    order: int = Form(None),  # Training
    sets: int = Form(None),  # Training
    reps: int = Form(None),  # Training
    weight: float = Form(None),  # Training
    rest_seconds: int = Form(None),  # Training
    meal_name: str = Form(None),  # Diet
    food_name: str = Form(None),  # Diet
    quantity: str = Form(None),  # Diet
    name: str = Form(None),  # Steroid
    type: str = Form(None),  # Steroid
    dosage: str = Form(None),  # Steroid
    frequency: str = Form(None),  # Steroid
    notes: str = Form(None),
):
    pb = request.state.pb
    tenant = request.state.tenant.id
    data = {"plan": plan, "notes": notes}
    collection_name = f"{plan_type}_items"

    # Mapping logic per collection
    if plan_type == "training":
        data.update(
            {
                "name": item_name,
                "seq": seq,
                "order": order,
                "sets": sets,
                "reps": reps,
                "weight": weight,
                "rest_seconds": rest_seconds,
            }
        )
    elif plan_type == "diet":
        data.update(
            {
                "name": food_name,
                "meal_name": meal_name,
                "quantity": quantity,
                "seq": seq,
                "order": order,
            }
        )
    elif plan_type == "steroid":
        data.update(
            {
                "name": name,
                "type": type,
                "dosage": dosage,
                "frequency": frequency,
                "seq": seq,
                "order": order,
            }
        )

    try:
        create_item(pb, tenant, collection_name, data)

        # 🟢 SUCCESS: Close modal and show success toast!
        trigger_data = {
            "closeModal": True,
            "show-toast": {"message": "آیتم با موفقیت اضافه شد.", "type": "success"},
        }
        return HTMLResponse(status_code=204, headers={"HX-Trigger": json.dumps(trigger_data)})

    except Exception as e:
        from structlog import get_logger

        logger = get_logger(__name__)
        logger.error("item.create_failed", error=str(e), plan_type=plan_type, plan=plan)
        # 🔴 ERROR: Keep modal open and show error toast!
        trigger_data = {
            "show-toast": {"message": "مشکلی پیش آمد. لطفا دوباره تلاش کنید.", "type": "error"}
        }
        return HTMLResponse(status_code=204, headers={"HX-Trigger": json.dumps(trigger_data)})


@router.post("/items/{id}")
async def item_update(
    request: Request,
    id: str,
    plan_type: str = Form(...),
    plan: str = Form(None),
    item_name: str = Form(None),  # Training
    seq: int = Form(None),  # Training (Day)
    order: int = Form(None),  # Training
    sets: int = Form(None),  # Training
    reps: int = Form(None),  # Training
    weight: float = Form(None),  # Training
    rest_seconds: int = Form(None),  # Training
    meal_name: str = Form(None),  # Diet
    food_name: str = Form(None),  # Diet
    quantity: str = Form(None),  # Diet
    name: str = Form(None),  # Steroid
    type: str = Form(None),  # Steroid
    dosage: str = Form(None),  # Steroid
    frequency: str = Form(None),  # Steroid
    notes: str = Form(None),
):
    pb = request.state.pb
    collection_name = f"{plan_type}_items"

    # Base data
    data = {"notes": notes}

    # Only send plan if it's a valid ID (prevents the 400 error)
    if plan and not plan.startswith(plan_type):
        data["plan"] = plan

    # Mapping logic per collection
    if plan_type == "training":
        data.update(
            {
                "name": item_name,
                "seq": seq,
                "order": order,
                "sets": sets,
                "reps": reps,
                "weight": weight,
                "rest_seconds": rest_seconds,
            }
        )
    elif plan_type == "diet":
        data.update(
            {
                "name": food_name,
                "meal_name": meal_name,
                "quantity": quantity,
                "seq": seq,
                "order": order,
            }
        )
    elif plan_type == "steroid":
        data.update(
            {
                "name": name,
                "type": type,
                "dosage": dosage,
                "frequency": frequency,
                "seq": seq,
                "order": order,
            }
        )

    try:
        # Call your service with CORRECT ORDER: (pb, id, collection_name, data)
        update_item(pb, id, collection_name, data)

        # 🟢 SUCCESS: Close modal, refresh the list, and show success toast!
        trigger_data = {
            "closeModal": True,
            "refreshList": True,
            "show-toast": {"message": "آیتم با موفقیت ویرایش شد.", "type": "success"},
        }
        return HTMLResponse(status_code=204, headers={"HX-Trigger": json.dumps(trigger_data)})

    except Exception as e:
        from structlog import get_logger

        logger = get_logger(__name__)
        logger.error("item.update_failed", error=str(e), item_id=id, plan_type=plan_type)
        # 🔴 ERROR: Keep modal open and show error toast!
        trigger_data = {
            "show-toast": {"message": "مشکلی پیش آمد. لطفا دوباره تلاش کنید.", "type": "error"}
        }
        return HTMLResponse(status_code=204, headers={"HX-Trigger": json.dumps(trigger_data)})
