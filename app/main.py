print("DEBUG: starting main.py")

from fastapi import FastAPI
print("DEBUG: imported FastAPI")

from fastapi.middleware.cors import CORSMiddleware
print("DEBUG: imported CORSMiddleware")

from apscheduler.schedulers.background import BackgroundScheduler
print("DEBUG: imported APScheduler")

# Import your routes AFTER FastAPI setup
from app.routes import video, feeder, manual_feed, once_schedule
print("DEBUG: imported routes")

from app.services.feeder_service import check_and_trigger_schedule
print("DEBUG: imported feeder_service")

from app.routes.sensors import send_sensor_realtime, send_sensor_hourly
print("DEBUG: imported sensors")

# ✅ Create FastAPI app
app = FastAPI()
print("DEBUG: FastAPI app created")

# ✅ Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
print("DEBUG: middleware added")

# ✅ Include routers — only after app is defined
app.include_router(video.video_route)
print("DEBUG: video router included")

app.include_router(manual_feed.feed_route)
print("DEBUG: manual_feed router included")

app.include_router(feeder.feeder_route)
print("DEBUG: feeder router included")

app.include_router(once_schedule.once_route)
print("DEBUG: once_schedule router included")

# ✅ Root endpoint
@app.get("/")
def root():
    return {"message": "FastAPI is running!"}
print("DEBUG: root endpoint added")

# ✅ Scheduler setup
scheduler = BackgroundScheduler()
print("DEBUG: scheduler created")




@app.on_event("startup")
def on_startup():
    print("DEBUG: startup event running")
    scheduler.add_job(check_and_trigger_schedule, "interval", minutes=1)
    scheduler.add_job(send_sensor_realtime, "interval", seconds=3)
    scheduler.add_job(send_sensor_hourly, "interval", hours=1)
    scheduler.start()
    print("DEBUG: scheduler started")

@app.on_event("shutdown")
def on_shutdown():
    if scheduler.running:
        scheduler.shutdown()
    print("🛑 Scheduler stopped")
