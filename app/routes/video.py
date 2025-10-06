import cv2
import asyncio
import threading
import time
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse, JSONResponse
from run import aquarium
import os
from dotenv import load_dotenv
from app.routes import verify_key
import subprocess  # <-- added for ffmpeg-based manager

load_dotenv()

header = os.getenv("secret_api")

video_route = APIRouter()

TARGET_WIDTH = 320
TARGET_HEIGHT = 240
FPS = 15
JPEG_QUALITY = 20


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


# ---------------------------
# New FFmpeg-based manager
# ---------------------------
class FFmpegCameraManager:
    def __init__(self):
        self.proc = None
        self.running = False
        self.frame = None
        self.lock = threading.Lock()
        self.thread = None

    def start(self):
        if self.running:
            return

        self.proc = subprocess.Popen([
            "ffmpeg",
            "-f", "v4l2",
            "-framerate", str(FPS),
            "-video_size", f"{TARGET_WIDTH}x{TARGET_HEIGHT}",
            "-i", "/dev/video0",
            "-vf", f"fps={FPS},scale={TARGET_WIDTH}:{TARGET_HEIGHT}",
            "-q:v", str(31 - int(JPEG_QUALITY / 3)),  # approximate mapping
            "-f", "mjpeg", "-"  # MJPEG stream to stdout
        ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10**7)

        self.running = True
        self.thread = threading.Thread(target=self._update_frames, daemon=True)
        self.thread.start()

    def _update_frames(self):
        buffer = b""
        while self.running and self.proc and self.proc.stdout:
            data = self.proc.stdout.read(4096)
            if not data:
                time.sleep(0.1)
                continue
            buffer += data
            start = buffer.find(b"\xff\xd8")
            end = buffer.find(b"\xff\xd9")
            if start != -1 and end != -1 and end > start:
                frame = buffer[start:end+2]
                buffer = buffer[end+2:]
                with self.lock:
                    self.frame = frame

    def stop(self):
        self.running = False
        if self.proc:
            self.proc.kill()
        self.proc = None
        self.frame = None

    def get_frame(self):
        with self.lock:
            return self.frame


# Switch between OpenCV or FFmpeg camera manager here
camera_manager = CameraManager()
# camera_manager = FFmpegCameraManager()  # uncomment to use ffmpeg instead


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
        await asyncio.sleep(0)


@video_route.get(f"/aquarium/{aquarium}/video_feed")
# @video_route.get(f"/aquarium/{aquarium}/video_feed", dependencies=[Depends(verify_key)])
async def video_feed():
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@video_route.post(f"/aquarium/{aquarium}/camera_switch/{{switch}}")
def set_camera_switch(switch: bool):
    try:
        if switch:
            camera_manager.start()
        else:
            camera_manager.stop()
        return {"Message": f"Camera {'opened' if switch else 'closed'} successfully"}
    except Exception as e:
        return JSONResponse({"Message": str(e)}, status_code=500)