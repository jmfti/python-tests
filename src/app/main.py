from gc import collect
from typing import Optional, List
from config import get_config
from pymongo import errors
import motor.motor_asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr
from pydantic import Field
from routers import meetings, metrics_controller
import logging, logging.config
import asyncio
from starlette_prometheus import metrics, PrometheusMiddleware
# from metrics.scheduled_tasks import collect_metrics
import random, os
from prometheus_client import start_http_server
from routers.metrics_controller import set_metrics_gen_status
from common.utils import Repository


cfg = get_config()
formatter = logging.Formatter("%(asctime)s loglevel=%(levelname)-6s logger=%(name)s %(funcName)s() L%(lineno)-4d %(message)s   call_trace=%(pathname)s L%(lineno)-4d")
logger = logging.getLogger("app")
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
logger.addHandler(ch)

import pandas as pd
iris = pd.read_csv('https://raw.githubusercontent.com/mwaskom/seaborn-data/master/iris.csv')
print(iris.head(15))

print("pruebaaaaaaa")
# logging.config.fileConfig('logging.conf', disable_existing_loggers=False)

app = FastAPI()
app.include_router(meetings.router)
app.include_router(metrics_controller.router)
app.add_middleware(PrometheusMiddleware)
app.add_route("/metrics", metrics)

@app.on_event("startup")
async def prepare_things():
    env = dict(os.environ)
    try:
        start_http_server(8000) 
    except OSError as e:
        # it just means a worker already opened the server, so pass through
        pass
    if env["ENVIRONMENT"] == "DEV":
        await set_metrics_gen_status(True)
    

# spawn another thread to handle metrics gathering
#start_http_server(8000)