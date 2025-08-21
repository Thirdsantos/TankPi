import cv2
import asyncio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from run import aquarium

video_route = APIRouter()
cap = cv2.VideoCapture(0)

TARGET_WIDTH = 160   # lower resolution for smoothness
TARGET_HEIGHT = 120
FPS = 30             # higher FPS
JPEG_QUALITY = 30    # lowest acceptable quality for speed

cap.set(cv2.CAP_PROP_FRAME_WIDTH, TARGET_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, TARGET_HEIGHT)
cap.set(cv2.CAP_PROP_FPS, FPS)

if not cap.isOpened():
    raise RuntimeError("Cannot open camera")

async def generate_frames():
    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        # Resize to reduce load
        frame = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT))

        # Encode as JPEG
        ret, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
        frame_bytes = buffer.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
        )

        await asyncio.sleep(0)  # give event loop control

@video_route.get(f"/aquarium/{aquarium}/video_feed")
async def video_feed():
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
