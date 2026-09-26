from fastapi import APIRouter, Request, Form, Query
import csv
import functools
import json
from app.services.item import get_item_by_id, create_item, update_item
from app.services.plan import get_plan_by_id
from ..templates import templates
from fastapi.responses import HTMLResponse
from fastapi.responses import RedirectResponse
from app.security import sanitize_collection_name
from structlog import get_logger
from app.i18n import _

logger = get_logger(__name__)

router = APIRouter(tags=["items Management"])


# ponytail: whole-file read + unique in memory; datasets are small (~thousands rows).
# Swap to DB-backed suggestions if the CSVs ever become a data source of record.
@functools.lru_cache(maxsize=None)
def _unique_names(path: str, column: str) -> tuple:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return tuple(
            {
                row[column].strip()
                for row in csv.DictReader(f)
                if row.get(column) and row[column].strip()
            }
        )


def _exercise_names():
    return list(_unique_names("data/Fitness_Exercises_Dataset.csv", "Exercise Name"))


def _food_names():
    return list(_unique_names("data/Diet_Foods_Dataset.csv", "Food Name"))


# Get Requests
@router.get("/items/new")
def item_edit_form(request: Request, plan_type: str = Query(...), plan_id: str = Query(...)):
    tenant = request.state.tenant.id
    try:
        collection_name = sanitize_collection_name(plan_type)
    except ValueError:
        return HTMLResponse(content="Invalid plan_type", status_code=400)
    user = request.state.user

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")
    # Verify plan belongs to tenant
    try:
        get_plan_by_id(request.state.pb, tenant, plan_id)
    except Exception:
        return HTMLResponse(content="Plan not found", status_code=404)

    return templates.TemplateResponse(
        request=request,
        name="modals/items_form.html",
        context={
            "title": _("Edit item"),
            "tenant": tenant,
            "plan_type": plan_type,
            "plan_id": plan_id,
            "collection_name": collection_name,
            "item": None,
            "exercise_names": _exercise_names(),
            "food_names": _food_names(),
        },
    )


@router.get("/items/{id}/edit")
def item_edit_form_by_id(request: Request, id: str, plan_type: str = Query(...)):
    pb = request.state.pb
    tenant = request.state.tenant.id
    user = request.state.user
    try:
        collection_name = sanitize_collection_name(plan_type)
    except ValueError:
        return HTMLResponse(content="Invalid plan_type", status_code=400)
    try:
        item = get_item_by_id(pb, tenant, collection_name, id)
    except Exception:
        return HTMLResponse(content="Item not found", status_code=404)
    tenant_name = request.state.tenant

    if user.role == "trainee":
        return RedirectResponse(url="/user/dashboard")

    return templates.TemplateResponse(
        request=request,
        name="modals/items_form.html",
        context={
            "title": _("Edit item"),
            "tenant": tenant_name,
            "item": item,
            "plan_type": plan_type,
            "collection_name": collection_name,
            "exercise_names": _exercise_names(),
            "food_names": _food_names(),
        },
    )


# Delete requests
@router.delete("/items/{id}")
def item_delete(request: Request, id: str, plan_type: str = Query(...)):
    pb = request.state.pb
    tenant = request.state.tenant.id
    try:
        collection_name = sanitize_collection_name(plan_type)
    except ValueError:
        return HTMLResponse(content="Invalid plan_type", status_code=400)

    try:
        # Verify item ownership before delete
        get_item_by_id(pb, tenant, collection_name, id)
        from app.services.item import delete_item

        delete_item(pb, id, collection_name)

        # 🟢 SUCCESS: Close modal, refresh the list, and show success toast!
        trigger_data = {
            "closeModal": True,
            "refreshList": True,
            "show-toast": {"message": _("Item deleted successfully."), "type": "success"},
        }
        return HTMLResponse(status_code=204, headers={"HX-Trigger": json.dumps(trigger_data)})

    except Exception as e:
        logger.error("item.delete_failed", error=str(e), item_id=id, plan_type=plan_type)
        # 🔴 ERROR: Keep modal open and show error toast!
        trigger_data = {
            "show-toast": {"message": _("Something went wrong. Please try again."), "type": "error"}
        }
        return HTMLResponse(status_code=204, headers={"HX-Trigger": json.dumps(trigger_data)})


# Confirm delete modal
@router.get("/items/{id}/confirm-delete")
def item_confirm_delete(request: Request, id: str, plan_type: str = Query(...)):
    return templates.TemplateResponse(
        "modals/confirm_delete.html",
        {
            "request": request,
            "title": _("Delete item"),
            "delete_url": f"/items/{id}?plan_type={plan_type}",
        },
    )


# Post requests
@router.post("/items")
def item_create(
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
    category: str = Form(None),  # Training
    notes: str = Form(None),
):
    pb = request.state.pb
    tenant = request.state.tenant.id
    try:
        collection_name = sanitize_collection_name(plan_type)
    except ValueError:
        trigger_data = {"show-toast": {"message": _("Invalid plan type"), "type": "error"}}
        return HTMLResponse(status_code=400, headers={"HX-Trigger": json.dumps(trigger_data)})
    # Verify plan belongs to tenant and type matches
    try:
        plan_obj = get_plan_by_id(pb, tenant, plan)
        if str(getattr(plan_obj, "type", "")) != plan_type:
            raise ValueError("type mismatch")
        # Coach can only add to own plans
        user = request.state.user
        if getattr(user, "role", None) == "coach" and str(getattr(plan_obj, "coach", "")) != str(
            user.id
        ):
            trigger_data = {"show-toast": {"message": _("Access denied"), "type": "error"}}
            return HTMLResponse(status_code=403, headers={"HX-Trigger": json.dumps(trigger_data)})
    except Exception as e:
        logger.warning("item.create_plan_check_failed", error=str(e), plan=plan)
        trigger_data = {"show-toast": {"message": _("Plan not found"), "type": "error"}}
        return HTMLResponse(status_code=404, headers={"HX-Trigger": json.dumps(trigger_data)})
    # Input length validation
    if notes:
        notes = str(notes)[:1000]
    data = {"plan": plan, "notes": notes}

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
                "category": category,
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
            "show-toast": {"message": _("Item added successfully."), "type": "success"},
        }
        return HTMLResponse(status_code=204, headers={"HX-Trigger": json.dumps(trigger_data)})

    except Exception as e:
        logger.error("item.create_failed", error=str(e), plan_type=plan_type, plan=plan)
        # 🔴 ERROR: Keep modal open and show error toast!
        trigger_data = {
            "show-toast": {"message": _("Something went wrong. Please try again."), "type": "error"}
        }
        return HTMLResponse(status_code=204, headers={"HX-Trigger": json.dumps(trigger_data)})


@router.post("/items/{id}")
def item_update(
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
    category: str = Form(None),  # Training
    notes: str = Form(None),
):
    pb = request.state.pb
    tenant = request.state.tenant.id
    try:
        collection_name = sanitize_collection_name(plan_type)
    except ValueError:
        trigger_data = {"show-toast": {"message": _("Invalid plan type"), "type": "error"}}
        return HTMLResponse(status_code=400, headers={"HX-Trigger": json.dumps(trigger_data)})
    # Verify existing item tenant ownership
    try:
        get_item_by_id(pb, tenant, collection_name, id)
        # If plan change requested, verify new plan belongs to tenant
        if plan:
            plan_obj = get_plan_by_id(pb, tenant, plan)
            if str(getattr(plan_obj, "type", "")) != plan_type:
                raise ValueError("type mismatch")
    except Exception:
        trigger_data = {"show-toast": {"message": _("Item not found"), "type": "error"}}
        return HTMLResponse(status_code=404, headers={"HX-Trigger": json.dumps(trigger_data)})

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
                "category": category,
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
            "show-toast": {"message": _("Item updated successfully."), "type": "success"},
        }
        return HTMLResponse(status_code=204, headers={"HX-Trigger": json.dumps(trigger_data)})

    except Exception as e:
        logger.error("item.update_failed", error=str(e), item_id=id, plan_type=plan_type)
        # 🔴 ERROR: Keep modal open and show error toast!
        trigger_data = {
            "show-toast": {"message": _("Something went wrong. Please try again."), "type": "error"}
        }
        return HTMLResponse(status_code=204, headers={"HX-Trigger": json.dumps(trigger_data)})
