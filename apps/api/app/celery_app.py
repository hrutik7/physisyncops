import os
from dotenv import load_dotenv
from celery import Celery

# Load environment variables from .env file
load_dotenv()

celery_app = Celery("opentra")

celery_app.conf.update(
    broker_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    result_backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    include=["app.tasks"],
    task_routes={"app.tasks.*": {"queue": "opentra"}}
)
