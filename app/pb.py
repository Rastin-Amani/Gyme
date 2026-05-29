import os
from pocketbase import PocketBase

# Fetches PB_URL from the environment, defaults to local if not set
PB_URL = os.getenv("PB_URL", "http://127.0.0.1:8091")
pb = PocketBase(PB_URL)

def get_pb():
    return PocketBase(PB_URL)