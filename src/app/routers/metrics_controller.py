from dataclasses import dataclass
from re import A
from typing import Dict, List, Optional, Union
import typing
from dataclasses import field
from typing_extensions import Self
import motor.motor_asyncio
import datetime
import json
import hashlib
from pydantic import BaseModel
import fastapi 
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
import asyncio
# from fastapi.logger import logger
import logging
from fastapi.encoders import jsonable_encoder
import random
import prometheus_client
import typing

from prometheus_client import Counter, Gauge, Histogram, start_http_server

logger = logging.getLogger("app")
FORMAT = "%(processName)s %(name)s %(filename)s %(module)s %(funcName)s %(levelname)s %(lineno)d %(message)s"
# logger.info(logger.__format__)


router = APIRouter(
    prefix="/metrics_generator",
    tags=["metrics_generator"],
    dependencies=[],
    responses={404: {"description": "Not Found"}}
)

class StatusModel(BaseModel):
    status: str
    data : Dict

class GenericResponse(BaseModel):
    code: int
    data: Dict
    
# state pattern for handling state
class StateMetricsGenerator:
    def set_status(self, status: bool, context):
        """ """
    
    def get_status(self ) -> bool:
        """ """

class ActivatedMetricsGenerator(StateMetricsGenerator):
    def set_status(self, status: bool, context):
        if status == True:
            return self
        # deactivate
        context.metrics_task.cancel()
        return DeActivatedMetricsGenerator()

    def get_status(self) -> bool:
        return True
    

class DeActivatedMetricsGenerator(StateMetricsGenerator):
    def set_status(self, status: bool, context):
        logger.info("set_status is called")
        if status == False:
            return self
        # if we have to activate it
        try:
            loop = asyncio.get_event_loop()                           
            if loop is None: 
                return self
            context.metrics_task = asyncio.create_task(context.collect_metrics())
            loop.call_later(context.sleep_time, context.metrics_task)                          
            return ActivatedMetricsGenerator()
        except Exception as e:
            e.with_traceback()
            pass
        return self

    def get_status(self) -> bool:
        return False

    

class MetricsGenerator:
    state: StateMetricsGenerator
    sleep_time: int
    metrics_task: None
    QUEUES_LENGTHS = Gauge(
        "task_queue_length", "Number of elements in the task queues by queue_name", ["queue_name"]
    )
    def __init__(self, sleep_time):
        self.state = DeActivatedMetricsGenerator()
        self.sleep_time = sleep_time
        
        self.metrics_task = None #asyncio.create_task(self.collect_metrics())
    
    def set_status(self, active: bool) -> bool:
        """this just calls state.set_status which returns the next state based on input

        Args:
            active (bool): 

        Returns:
            bool: 
        """
        # this should be decoupled
        previous_state = self.state.get_status()
        self.state = self.state.set_status(active, self)
        current_state = self.state.get_status()
        if previous_state != current_state:
            logger.info("changed status")
        return current_state
    
    def get_status(self):
        return self.state.get_status()
    
    
    async def collect_metrics(self):
        """just generates random data and shares the info with prometheus publisher
        """
        while True:
            logger.info("generating random metrics for queue_1")
            self.QUEUES_LENGTHS.labels("queue_1").set(random.randint(0,20))
            await asyncio.sleep(self.sleep_time)  # this should be changed to a variable, retrieved from a config yaml or json
    
    

metrics_gen = MetricsGenerator(sleep_time=5)


@router.get("/status/{active}", response_description="", status_code=status.HTTP_200_OK, response_model=StatusModel)
async def set_metrics_gen_status(active: bool) -> StatusModel:
    global metrics_gen 
    
    result = metrics_gen.set_status(active)
    return StatusModel(status= "on" if result == True else "off", data={}) # TODO change to bool, more natural




    """get status 

    Returns:
        StatusModel: 
    """
@router.get("/status", response_description="", status_code=status.HTTP_200_OK, response_model=StatusModel)
async def get_metrics_status() -> StatusModel:
    global metrics_gen
    return StatusModel(status= "on" if metrics_gen.get_status() == True else "off", data={})
    
    
    
# @router.get("/activate_new_thread", response_description="", status_code=status.HTTP_200_OK, response_model=GenericResponse)
# async def spawn_prometheus_thread() -> GenericResponse:
#     start_http_server(8000)
#     return GenericResponse(code=200, data={"result": "ok"})