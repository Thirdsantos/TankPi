from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import video, feeder
from app.routes.sensors import send_sensor_realtime, send_sensor_hourly
from apscheduler.schedulers.background import BackgroundScheduler

app = FastAPI()
scheduler = BackgroundScheduler()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(video.video_route)
app.include_router(feeder.feeder_route)

# ------------------------
# Schedule Jobs
# ------------------------
scheduler.add_job(
    send_sensor_realtime,
    "interval",
    seconds=3,
    max_instances=1,
    coalesce=True,
    replace_existing=True
)

scheduler.add_job(
    send_sensor_hourly, 
    "interval",
    hours=1,
    max_instances=1,
    coalesce=True,
    replace_existing=True
)

scheduler.start()
