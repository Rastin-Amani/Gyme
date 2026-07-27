from pocketbase.models import FileUpload


def create_progress_log(pb, data: dict, file_uploads=None):
    """Creates a new progress log in PocketBase."""
    if file_uploads:
        data["progress_photos"] = FileUpload(*file_uploads)
    return pb.collection("progress_logs").create(data)


def get_progress_log_by_id(pb, log_id: str):
    """Fetches a single progress log by ID."""
    return pb.collection("progress_logs").get_one(log_id)


def update_progress_log(pb, log_id: str, data: dict, file_uploads=None):
    """Updates a progress log in PocketBase."""
    if file_uploads:
        data["progress_photos"] = FileUpload(*file_uploads)
    return pb.collection("progress_logs").update(log_id, data)


def get_progress_logs_by_trainee(pb, tenant_id: str, trainee_id: str):
    """Fetches all progress logs for a specific trainee, sorted by newest."""
    return pb.collection("progress_logs").get_full_list(
        query_params={
            "filter": f'tenant="{tenant_id}" && trainee="{trainee_id}"',
            "sort": "-created",
        }
    )
