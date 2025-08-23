from fastapi import APIRouter, WebSocket
from run import aquarium
from starlette.websockets import WebSocketDisconnect

feeder_route = APIRouter()

@feeder_route.websocket("/aquarium/{aquarium}/feeder_switch")
async def feeder(websocket: WebSocket):
  await websocket.accept()
  try: 
    while True:
      data = await websocket.receive_json()
      switch = data["status"]

      if switch:
        print("Auto feeder is on")
      else:
        print("Auto feeder is off")
      
  
  except WebSocketDisconnect:
    print("Client Disconnected")



