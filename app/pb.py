from pocketbase import Pocetkbase

PB_URL = "http://127.0.0.1:8090"


def get_pb():
    return Pocetkbase(PB_URL)
