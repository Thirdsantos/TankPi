from fastapi import FastAPI
from app.routes import video
from app.routes.sensors import send_sensor_realtime, send_sensor_hourly
from apscheduler.schedulers.background import BackgroundScheduler


app = FastAPI()
scheduler = BackgroundScheduler()


app.include_router(video.video_route)

scheduler.add_job(send_sensor_realtime, 'interval', seconds = 3)
scheduler.add_job(send_sensor_hourly, 'interval', hours = 1)

scheduler.start()






