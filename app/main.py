from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import video
from app.routes.sensors import send_sensor_realtime, send_sensor_hourly
from apscheduler.schedulers.background import BackgroundScheduler

app = FastAPI()
scheduler = BackgroundScheduler()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # allow all origins (can restrict later)
    allow_methods=["*"],   # allow all HTTP methods
    allow_headers=["*"],   # allow all headers
)

# Include video routes
app.include_router(video.video_route)

# ------------------------
# Schedule Jobs
# ------------------------
scheduler.add_job(
    send_sensor_realtime,
    "interval",
    seconds=3,
    max_instances=1,
    coalesce=True
)

scheduler.add_job(
    send_sensor_hourly,
    "interval",
    hours=1,
    max_instances=1,
    coalesce=True
)

#scheduler.start()