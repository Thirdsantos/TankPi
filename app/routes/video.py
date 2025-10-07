import cv2
import asyncio
import threading
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse
from run import aquarium
import os
from dotenv import load_dotenv

load_dotenv()

video_route = APIRouter()

TARGET_WIDTH = 320
TARGET_HEIGHT = 240
FPS = 15
JPEG_QUALITY = 20


# ---------------------------
# Camera Manager
# ---------------------------
class CameraManager:
    def __init__(self):
        self.cap = None
        self.running = False
        self.frame = None
        self.lock = threading.Lock()
        self.thread = None

    def start(self):
        if self.running:
            return
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, TARGET_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, TARGET_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, FPS)

        if not self.cap.isOpened():
            self.cap = None
            raise RuntimeError("Cannot open camera")

        self.running = True
        self.thread = threading.Thread(target=self._update_frames, daemon=True)
        self.thread.start()

    def _update_frames(self):
        while self.running and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.1)
                continue
            frame = cv2.resize(frame, (TARGET_WIDTH, TARGET_HEIGHT))
            with self.lock:
                self.frame = frame
            time.sleep(1 / FPS)

    def stop(self):
        self.running = False
        if self.cap and self.cap.isOpened():
            self.cap.release()
        self.cap = None
        self.frame = None

    def get_frame(self):
        with self.lock:
            if self.frame is None:
                return None
            ret, buffer = cv2.imencode(".jpg", self.frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
            if not ret:
                return None
            return buffer.tobytes()


camera_manager = CameraManager()


# ---------------------------
# MJPEG generator
# ---------------------------
async def generate_frames():
    while True:
        if not camera_manager.running:
            await asyncio.sleep(0.1)
            continue
        frame = camera_manager.get_frame()
        if frame:
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            )
        await asyncio.sleep(1 / FPS)


# ---------------------------
# MJPEG HTTP Endpoint (fallback)
# ---------------------------
@video_route.get("/aquarium/{aquarium}/video_feed")
async def video_feed(aquarium: str, request: Request):
    """
    Serve MJPEG stream over HTTP.
    Fallback for browsers that don't support WebSocket.
    """
    if not camera_manager.running:
        camera_manager.start()
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ---------------------------
# WebSocket Streaming Endpoint
# ---------------------------
@video_route.websocket("/aquarium/{aquarium}/video_feed_ws")
async def websocket_video(websocket: WebSocket, aquarium: str):
    """
    Fast WebSocket streaming as binary JPEG frames.
    Connect via: ws:// or wss://
    """
    await websocket.accept()
    print(f"✅ WebSocket client connected to aquarium {aquarium}")

    if not camera_manager.running:
        camera_manager.start()

    try:
        while True:
            frame = camera_manager.get_frame()
            if frame:
                try:
                    await asyncio.wait_for(websocket.send_bytes(frame), timeout=0.5)
                except asyncio.TimeoutError:
                    continue
            await asyncio.sleep(1 / FPS)

    except WebSocketDisconnect:
        print(f"👋 Client disconnected from aquarium {aquarium}")
    finally:
        camera_manager.stop()


# ---------------------------
# Camera On/Off Endpoint
# ---------------------------
@video_route.post("/aquarium/{aquarium}/camera_switch/{switch}")
def set_camera_switch(aquarium: str, switch: bool):
    try:
        if switch:
            camera_manager.start()
        else:
            camera_manager.stop()
        return {"Message": f"Camera {'opened' if switch else 'closed'} successfully"}
    except Exception as e:
        return JSONResponse({"Message": str(e)}, status_code=500)
