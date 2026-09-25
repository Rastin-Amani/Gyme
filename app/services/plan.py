from app.security import pb_escape, ALLOWED_PLAN_TYPES, sanitize_collection_name


def get_plans_by_trainee(pb, tenant, trainee_id):
    """Fetch all plans for a specific trainee within a tenant."""
    return pb.collection("plans").get_full_list(
        query_params={
            "filter": f'tenant="{pb_escape(tenant)}" && trainee="{pb_escape(trainee_id)}"',
            "sort": "-created",
            "expand": "trainee,coach,trainee.user",
        }
    )


def list_plans(
    pb,
    tenant,
    page=1,
    per_page=5,  # 🟢 Bump from 10 → 5
    query=None,
    type=None,
    coach_id=None,
    is_template=None,
    status=None,
    trainee=None,
):
    """List plans with optional filters."""
    from app.security import ALLOWED_PLAN_STATUS

    filters = [f'tenant="{pb_escape(tenant)}"']

    if query:
        safe_q = pb_escape(str(query)[:50])
        if safe_q:
            filters.append(
                f'(template_name ~ "{safe_q}" || trainee.user.first_name ~ "{safe_q}" || trainee.user.last_name ~ "{safe_q}")'
            )
    if type and type in ALLOWED_PLAN_TYPES:
        filters.append(f'type="{pb_escape(type)}"')
    if coach_id:
        filters.append(
            f'coach="{pb_escape(coach_id)}"'
        )  # Make sure this matches your DB relation name

    # 🟢 PocketBase Boolean Fields: NO QUOTES
    if is_template is True:
        filters.append("is_template=true")
    elif is_template is False:
        filters.append("is_template=false")
    elif is_template is None:
        # Default to showing non-templates if not specified
        filters.append("is_template=false")

    if status and status in ALLOWED_PLAN_STATUS:
        filters.append(f'status="{pb_escape(status)}"')
    if trainee:
        filters.append(f'trainee="{pb_escape(trainee)}"')

    filter_str = " && ".join(filters)
    query_params = {"sort": "-created"}

    if filter_str:
        query_params["filter"] = filter_str

    return pb.collection("plans").get_list(
        page=page,
        per_page=per_page,
        query_params={**query_params, "expand": "trainee,coach,trainee.user"},
    )


def get_plan_by_id(pb, tenant, id):
    """Get a single plan by ID."""
    return pb.collection("plans").get_first_list_item(
        f'tenant="{pb_escape(tenant)}" && id="{pb_escape(id)}"',
        query_params={"expand": "trainee,coach,trainee.user", "fields": "*,expand.*"},
    )


def get_template_by_id(pb, tenant, id):
    """Get a single template by ID (templates are stored in plans collection with is_template=true)."""
    return pb.collection("plans").get_first_list_item(
        f'tenant="{pb_escape(tenant)}" && id="{pb_escape(id)}" && is_template=true',  # 🟢 NO QUOTES
        query_params={"expand": "trainee,coach,trainee.user"},
    )


def create_plan(pb, tenant, data: dict):
    """Create a new plan."""
    payload = {
        **data,
        "tenant": tenant,
    }
    return pb.collection("plans").create(payload)


def update_plan(pb, tenant, plan_id, data: dict):
    """Update an existing plan - verifies tenant ownership."""
    # Verify tenant owns plan before update (prevent IDOR)
    get_plan_by_id(pb, tenant, plan_id)
    # Sanitize data: only allow safe fields, tenant/is_template not overwriteable arbitrarily
    safe_data = {}
    allowed = {
        "type",
        "trainee",
        "start_date",
        "end_date",
        "days_per_week",
        "status",
        "notes",
        "is_template",
        "template_name",
        "coach",
    }
    for k, v in (data or {}).items():
        if k not in allowed:
            continue
        if k == "type" and v not in ALLOWED_PLAN_TYPES:
            continue
        if k == "status":
            from app.security import ALLOWED_PLAN_STATUS

            if v not in ALLOWED_PLAN_STATUS:
                continue
        safe_data[k] = v
    return pb.collection("plans").update(pb_escape(plan_id), safe_data)


def delete_plan(pb, tenant, plan_id):
    """Delete a plan by ID - verifies tenant ownership."""
    get_plan_by_id(pb, tenant, plan_id)
    return pb.collection("plans").delete(pb_escape(plan_id))


# Backwards compat for older callers that used update_plan(pb, id, data) without tenant
def _legacy_update_plan(pb, plan_id, data: dict):
    return pb.collection("plans").update(pb_escape(plan_id), data)


def list_templates(pb, tenant, page=1, per_page=5):
    """List all templates for a tenant."""
    # 🟢 FIXED: Queries plans where is_template=true
    return pb.collection("plans").get_list(
        page=page,
        per_page=per_page,
        query_params={
            "filter": f'tenant="{pb_escape(tenant)}" && is_template=true',  # 🟢 NO QUOTES
            "sort": "-created",
        },
    )


def apply_template(
    pb, tenant, template_id, trainee_id, coach_id=None, start_date=None, end_date=None, notes=None
):
    """Apply a template to a trainee, duplicating all items."""
    # 1. Fetch the template
    template = get_template_by_id(pb, tenant, template_id)
    # Validate template type is allowlisted
    if str(template.type) not in ALLOWED_PLAN_TYPES:
        raise ValueError("Invalid template type")
    # Validate trainee belongs to same tenant (defense in depth)
    from app.services.trainee import get_trainee_by_id

    try:
        get_trainee_by_id(pb, tenant, trainee_id)
    except Exception as e:
        raise ValueError("Trainee not found in tenant") from e

    # 2. Build the new plan payload
    payload = {
        "trainee": trainee_id,
        "tenant": tenant,
        "coach": coach_id,
        "type": template.type,
        "is_template": False,  # 🟢 Ensure boolean False
        "status": "active",
        "days_per_week": getattr(template, "days_per_week", None),
        "start_date": start_date if start_date else getattr(template, "start_date", None),
        "end_date": end_date if end_date else getattr(template, "end_date", None),
        "notes": notes if notes else getattr(template, "notes", None),
        "template_name": "",  # Clear this out so it doesn't leak into trainee view
    }

    # 3. Create the new plan
    new_plan = pb.collection("plans").create(payload)

    # 4. Duplicate items from the template's type-specific collection
    collection_name = sanitize_collection_name(str(template.type))

    item_fields_by_type = {
        "training": ["name", "seq", "order", "sets", "reps", "weight", "rest_seconds", "notes"],
        "diet": ["name", "meal_name", "quantity", "seq", "order", "notes"],
        "steroid": ["name", "type", "dosage", "frequency", "seq", "order", "notes"],
    }
    copy_fields = item_fields_by_type.get(template.type, ["name", "notes"])

    try:
        template_items = pb.collection(collection_name).get_full_list(
            query_params={
                "filter": f'tenant="{pb_escape(tenant)}" && plan="{pb_escape(template_id)}"',
                "sort": "+seq,+order",
            }
        )
        for item in template_items:
            item_data = {"plan": new_plan.id, "tenant": tenant}
            for field in copy_fields:
                val = getattr(item, field, None)
                if val is not None:
                    item_data[field] = val

            try:
                pb.collection(collection_name).create(item_data)
            except Exception as e:
                from structlog import get_logger

                logger = get_logger(__name__)
                logger.warning(
                    "template.item_copy_failed",
                    error=str(e),
                    item_id=getattr(item, "id", "?"),
                    template_id=template_id,
                )

    except Exception as e:
        from structlog import get_logger

        logger = get_logger(__name__)
        logger.warning(
            "template.items_fetch_failed",
            error=str(e),
            collection=collection_name,
            template_id=template_id,
        )

    return new_plan
