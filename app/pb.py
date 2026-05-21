from pocketbase import PocketBase

PB_URL = "http://127.0.0.1:8091"
pb = PocketBase(PB_URL)

def get_pb():
    return PocketBase(PB_URL)