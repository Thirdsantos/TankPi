from fastapi import APIRouter, Query
from app.services.feeder_service import handle_feeder_request
from threading import Lock

feeder_route = APIRouter(prefix="/feeder", tags=["Feeder"])
_feeder_lock = Lock()

@feeder_route.get("/")
def feeder(mode: str = Query("manual", enum=["manual", "schedule"])):
    if not _feeder_lock.acquire(blocking=False):
        return {"status": "busy", "message": "Feeder is already running. Please wait."}
    try:
        return handle_feeder_request(mode)
    finally:
        _feeder_lock.release()
