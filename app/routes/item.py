from fastapi import APIRouter, Request, Form, Query
from app.services.item import (
    list_items, get_item_by_id, create_item, update_item
    )
from ..templates import templates
from fastapi.responses import HTMLResponse

router = APIRouter(
    tags=["items Management"]
)

# Get Requests
@router.get("/items/new")
async def item_edit_form (request: Request, plan_type: str = Query(...)):
    tenant = request.state.tenant.id
    collection_name = f"{plan_type}_items"

    return templates.TemplateResponse(
        request=request,
        name="modals/items_form.html",
        context={
        "title" : "ویرایش آیتم",
        "tenant": tenant,
        "plan_type": plan_type,
        "collection_name": collection_name,
        "item": None,
        }
    )

@router.get("/items/{id}/edit")
async def item_edit_form (request: Request, id: str, plan_type: str = Query(...)):
    pb = request.state.pb
    tenant = request.state.tenant.id
    collection_name = f"{plan_type}_items"

    item = get_item_by_id(pb, tenant, collection_name, id)

    tenant_name = request.state.tenant
    return templates.TemplateResponse(
        request=request,
        name="modals/items_form.html",
        context={
        "title" : "ویرایش آیتم",
        "tenant": tenant_name,
        "item": item,
        "plan_type": plan_type,
        "collection_name": collection_name,
        }
    )

# Post requests
@router.post("/items")
async def item_create(
    request: Request,
    plan_type: str = Form(...),      
    plan: str = Form(None),          
    item_name: str = Form(None),     # Training
    seq: int = Form(None),           # Training (Day)
    order: int = Form(None),         # Training
    sets: int = Form(None),          # Training
    reps: int = Form(None),          # Training
    weight: float = Form(None),      # Training
    rest_seconds: int = Form(None),  # Training
    meal_name: str = Form(None),     # Diet
    food_name: str = Form(None),     # Diet
    quantity: str = Form(None),      # Diet
    name: str = Form(None),          # Steroid
    type: str = Form(None),          # Steroid
    dosage: str = Form(None),        # Steroid
    frequency: str = Form(None),     # Steroid
    notes: str = Form(None),
):
    pb = request.state.pb
    tenant = request.state.tenant.id
    data = {"notes": notes}

    # Only send plan if it's a valid ID (prevents the 400 error)
    if plan and not plan.startswith(plan_type):
        data["plan"] = plan

    # Mapping logic per collection
    if plan_type == "training":
        data.update({
            "name": item_name,
            "seq": seq,
            "order": order,
            "sets": sets,
            "reps": reps,
            "weight": weight,
            "rest_seconds": rest_seconds,
        })
    elif plan_type == "diet":
        data.update({
            "name": food_name,
            "meal_name": meal_name,
            "quantity": quantity,
            "seq": seq,
            "order": order,
        })
    elif plan_type == "steroid":
        data.update({
            "name": name,
            "type": type,
            "dosage": dosage,
            "frequency": frequency,
            "seq": seq,
            "order": order,
        })


    create_item(pb, tenant, plan_type, data)

    return HTMLResponse(status_code=204, headers={"HX-Trigger": "closeModal"})

@router.post("/items/{id}")
async def item_update(
    request: Request,
    id: str,
    plan_type: str = Form(...),      
    plan: str = Form(None),          
    item_name: str = Form(None),     # Training
    seq: int = Form(None),           # Training (Day)
    order: int = Form(None),         # Training
    sets: int = Form(None),          # Training
    reps: int = Form(None),          # Training
    weight: float = Form(None),      # Training
    rest_seconds: int = Form(None),  # Training
    meal_name: str = Form(None),     # Diet
    food_name: str = Form(None),     # Diet
    quantity: str = Form(None),      # Diet
    name: str = Form(None),          # Steroid
    type: str = Form(None),          # Steroid
    dosage: str = Form(None),        # Steroid
    frequency: str = Form(None),     # Steroid
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
        data.update({
            "name": item_name,
            "seq": seq,
            "order": order,
            "sets": sets,
            "reps": reps,
            "weight": weight,
            "rest_seconds": rest_seconds,
        })
    elif plan_type == "diet":
        data.update({
            "name": food_name,
            "meal_name": meal_name,
            "quantity": quantity,
            "seq": seq,
            "order": order,
        })
    elif plan_type == "steroid":
        data.update({
            "name": name,
            "type": type,
            "dosage": dosage,
            "frequency": frequency,
            "seq": seq,
            "order": order,
        })

    # Call your service with CORRECT ORDER: (pb, id, collection_name, data)
    update_item(pb, id, collection_name, data)

    # Trigger closeModal event to remove the modal from DOM
    return HTMLResponse(status_code=204, headers={"HX-Trigger": "closeModal, refreshList"})
