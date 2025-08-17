import cv2
import asyncio
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from run import aquarium  # your aquarium variable

video_route = APIRouter()

# ------------------------
# Camera Setup
# ------------------------
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

# Camera settings
TARGET_WIDTH = 320
TARGET_HEIGHT = 240
FPS = 15
JPEG_QUALITY = 30

cap.set(cv2.CAP_PROP_FRAME_WIDTH, TARGET_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, TARGET_HEIGHT)
cap.set(cv2.CAP_PROP_FPS, FPS)

if not cap.isOpened():
    print("Error: Cannot open camera")

on_off = True
latest_frame = None  # async frame buffer


# ------------------------
# Background Camera Capture Task
# ------------------------
async def capture_frames():
    global latest_frame
    while True:
        if on_off:
            ret, frame = cap.read()
            if ret:
                _, buffer = cv2.imencode(
                    ".jpg",
                    frame,
                    [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
                )
                latest_frame = buffer.tobytes()

        await asyncio.sleep(1 / FPS)


# Start background capture task
asyncio.create_task(capture_frames())


# ------------------------
# Camera REST Switch
# ------------------------
class SwitchRequest(BaseModel):
    switch: bool


@video_route.get("/")
def greetings():
    return "Hello World"


@video_route.post(f"/aquarium/{aquarium}/camera_switch")
def camera_switch(data: SwitchRequest):
    global on_off
    on_off = data.switch
    return {"camera_on": on_off}


# ------------------------
# MJPEG Stream (Low Latency)
# ------------------------
def mjpeg_stream():
    while True:
        if latest_frame:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + latest_frame + b"\r\n"
            )
        time.sleep(1 / FPS)


@video_route.get(f"/aquarium/{aquarium}/camera/mjpeg")
def mjpeg():
    return StreamingResponse(
        mjpeg_stream(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ------------------------
# Camera Control via WebSocket
# ------------------------
@video_route.websocket(f"/aquarium/{aquarium}/camera/control")
async def camera_control(websocket: WebSocket):
    global on_off
    await websocket.accept()

    try:
        while True:
            message = await websocket.receive_text()

            if message.lower() == "on":
                on_off = True
                await websocket.send_text("Camera ON")

            elif message.lower() == "off":
                on_off = False
                await websocket.send_text("Camera OFF")

    except WebSocketDisconnect:
        print("Control client disconnected")
