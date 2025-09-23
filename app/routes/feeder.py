from fastapi import APIRouter, Query
from app.services.feeder_service import handle_feeder_request

feeder_route = APIRouter(prefix="/feeder", tags=["Feeder"])

@feeder_route.get("/")
def feeder(mode: str = Query("manual", enum=["manual", "schedule"])):
    """
    Feeder endpoint.
    - manual → trigger feeder immediately
    - schedule → check current time vs backend schedule
    """
    return handle_feeder_request(mode)
