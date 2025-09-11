import cv2
import asyncio
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from run import aquarium
import os
from dotenv import load_dotenv
from app.routes import verify_key

load_dotenv()

header = os.getenv("secret_api")

video_route = APIRouter()
cap = cv2.VideoCapture(0)

TARGET_WIDTH = 160
TARGET_HEIGHT = 120
FPS = 60
JPEG_QUALITY = 30

cap.set(cv2.CAP_PROP_FRAME_WIDTH, TARGET_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, TARGET_HEIGHT)
cap.set(cv2.CAP_PROP_FPS, FPS)

if not cap.isOpened():
    raise RuntimeError("Cannot open camera")

camera_switch = True

async def generate_frames():
    global camera_switch, cap

    while camera_switch:
        ret, frame = cap.read()
        if not ret:
            await asyncio.sleep(0.1)
            continue

        frame = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT))
        ret, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
        frame_bytes = buffer.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )

        await asyncio.sleep(0)  # give control back to event loop



@video_route.get(f"/aquarium/{aquarium}/video_feed")
async def video_feed():
    global camera_switch

    if not camera_switch:
        return JSONResponse({"Message": "Camera Closed"})
    


    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@video_route.post("/aquarium/{aquarium}/camera_switch/{switch}")
def set_camera_switch(switch: bool):
    global camera_switch, cap
    camera_switch = switch

    if not switch:   # turn OFF
        cap.release()
        print("Camera off")
    else:            # turn ON again
        cap.open(0)
        print("Camera on")

    return {"Message": f"Succesfully set the switch {switch}"}
