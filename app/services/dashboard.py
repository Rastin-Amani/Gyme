from datetime import datetime, timedelta, timezone

def get_owner_dashboard_stats(pb, tenant_id: str, timeframe: str = "all"):
    # Base filter ensures we only get this specific owner's data
    base_filter = f'tenant="{tenant_id}"'

    # Calculate timeframes based on PocketBase's required UTC format
    if timeframe == "week":
        start_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S.000Z')
        base_filter += f' && created >= "{start_date}"'
    elif timeframe == "month":
        start_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S.000Z')
        base_filter += f' && created >= "{start_date}"'

    # Helper function to get the count efficiently
    def get_count(collection: str, extra_filter: str = ""):
        final_filter = base_filter
        if extra_filter:
            final_filter += f' && {extra_filter}'
        try:
            # We fetch 1 item per page just to read the 'total_items' metadata!
            result = pb.collection(collection).get_list(
                page=1, 
                per_page=1, 
                query_params={"filter": final_filter}
            )
            # Depending on your python sdk version, it might be total_items or totalItems
            return getattr(result, 'total_items', getattr(result, 'totalItems', 0))
        except Exception as e:
            print(f"Error fetching count for {collection}: {e}")
            return 0

    return {
        "active_trainees": get_count("trainees", 'status="active"'),
        "inactive_trainees": get_count("trainees", 'status="inactive"'),
        "diet_plans": get_count("plans", 'type="diet"'),
        "training_plans": get_count("plans", 'type="training"'),
        "steroid_plans": get_count("plans", 'type="steroid"')
    }