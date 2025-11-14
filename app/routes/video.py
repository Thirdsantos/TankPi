import cv2
import asyncio
import threading
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import StreamingResponse, JSONResponse
from run import aquarium 
from dotenv import load_dotenv

load_dotenv()

video_route = APIRouter()

aquarium_id_from_run = str(aquarium)

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
@video_route.get("/aquarium/{aquarium_id}/video_feed")
async def video_feed(aquarium_id: str, request: Request):
    """
    Serve MJPEG stream over HTTP.
    Fallback for browsers that don't support WebSocket.
    """
    # Check if URL aquarium_id matches the imported aquarium_id
    if aquarium_id != aquarium_id_from_run:
        return JSONResponse(
            {"Message": f"Error: Provided aquarium_id '{aquarium_id}' does not match the expected aquarium_id '{aquarium_id_from_run}'."},
            status_code=400
        )

    if not camera_manager.running:
        camera_manager.start()

    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ---------------------------
# WebSocket Streaming Endpoint
# ---------------------------
@video_route.websocket("/aquarium/{aquarium_id}/video_feed_ws")
async def websocket_video(websocket: WebSocket, aquarium_id: str):
    """
    Fast WebSocket streaming as binary JPEG frames.
    Connect via: ws:// or wss://
    """
    # Check if URL aquarium_id matches the imported aquarium_id
    if aquarium_id != aquarium_id_from_run:
        await websocket.close(code=1008)  # Close WebSocket connection with error code
        return

    await websocket.accept()
    print(f"✅ WebSocket client connected to aquarium {aquarium_id}")

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
        print(f"👋 Client disconnected from aquarium {aquarium_id}")
    finally:
        camera_manager.stop()


# ---------------------------
# Camera On/Off Endpoint
# ---------------------------
@video_route.post("/aquarium/{aquarium_id}/camera_switch/{switch}")
def set_camera_switch(aquarium_id: str, switch: bool):
    """
    Toggle the camera on/off based on the provided switch value.
    """
    # Check if URL aquarium_id matches the imported aquarium_id
    if aquarium_id != aquarium_id_from_run:
        return JSONResponse(
            {"Message": f"Error: Provided aquarium_id '{aquarium_id}' does not match the expected aquarium_id '{aquarium_id_from_run}'."},
            status_code=400
        )

    try:
        if switch:
            camera_manager.start()
        else:
            camera_manager.stop()

        return {"Message": f"Camera {'opened' if switch else 'closed'} successfully for aquarium {aquarium_id}"}
    except Exception as e:
        return JSONResponse({"Message": str(e)}, status_code=500)
