from pocketbase.models import FileUpload
from app.security import pb_escape


def create_progress_log(pb, data: dict, file_uploads=None):
    """Creates a new progress log in PocketBase."""
    if file_uploads:
        data["progress_photos"] = FileUpload(*file_uploads)
    return pb.collection("progress_logs").create(data)


def get_progress_log_by_id(pb, log_id: str):
    """Fetches a single progress log by ID."""
    return pb.collection("progress_logs").get_one(pb_escape(log_id))


def update_progress_log(pb, log_id: str, data: dict, file_uploads=None):
    """Updates a progress log in PocketBase."""
    if file_uploads:
        data["progress_photos"] = FileUpload(*file_uploads)
    return pb.collection("progress_logs").update(pb_escape(log_id), data)


def get_progress_logs_by_trainee(pb, tenant_id: str, trainee_id: str):
    """Fetches all progress logs for a specific trainee, sorted by newest."""
    return pb.collection("progress_logs").get_full_list(
        query_params={
            "filter": f'tenant="{pb_escape(tenant_id)}" && trainee="{pb_escape(trainee_id)}"',
            "sort": "-created",
        }
    )


def get_progress_log_with_tenant_check(pb, tenant_id: str, log_id: str):
    """Fetch log and verify tenant ownership, preventing IDOR."""
    log = get_progress_log_by_id(pb, log_id)
    rec_tenant = getattr(log, "tenant", None)
    if str(rec_tenant) != str(tenant_id):
        from pocketbase.errors import ClientResponseError

        raise ClientResponseError({"status": 404, "message": "Not found"}, 404, "Not found")
    return log
