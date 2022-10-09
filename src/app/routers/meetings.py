from dataclasses import dataclass
from typing import Dict, List, Optional, Union 
import motor.motor_asyncio
import datetime
import json
import hashlib
from pydantic import BaseModel
import pprint
import fastapi 
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
# from fastapi.logger import logger
import logging
from fastapi.encoders import jsonable_encoder
from prometheus_client import Summary
from caching import MonitoredTTLCache, caches
import traceback
from bson.objectid import ObjectId
from config import get_config
import re
from asyncache import cached
from utils import Repository
import cachetools 



import shelve


# from gunicorn.glogging import Logger
cfg = get_config()
logger = logging.getLogger("app")
FORMAT = "%(processName)s %(name)s %(filename)s %(module)s %(funcName)s %(levelname)s %(lineno)d %(message)s"
cache_meetings_find = MonitoredTTLCache(cache_name="meetings_find", maxsize=1000, ttl=3600)
cache_meetings_by_id = MonitoredTTLCache(cache_name="meetings_by_id", maxsize=1000, ttl=3600)
# logger.info(logger.__format__)

router = APIRouter(
    prefix="/meetings",
    tags=["meetings"],
    dependencies=[],
    responses={404: {"description": "Not Found"}}
)
meetings_async = motor.motor_asyncio.AsyncIOMotorClient(cfg["mongo_host"], cfg["mongo_port"]).demo.meetings
# Create a metric to track time spent and requests made.
REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request')

class GenericResponse(BaseModel):
    status: int
    message: str
    data: List

# just a class to represent a meeting of several people
class Meeting(BaseModel):
    datetime_from: datetime.datetime
    datetime_to: datetime.datetime 
    people: List[str]
    id: Optional[str] = None
    subject: str 
    content: str 
    signatures: List[str]
    


@REQUEST_TIME.time()
@router.get("/", response_description="Get all meetings", status_code=status.HTTP_200_OK, response_model=List[Meeting])
async def read_meetings(limit: Optional[int] = 1000, offset: Optional[int] = 0) -> List[Meeting]:
    """Gets paged elements

    Args:
        limit (Optional[int], optional): number of items to retrieve. Defaults to 1000.
        offset (Optional[int], optional): number of items to skip. Defaults to 0.

    Raises:
        HTTPException: No elements in database found

    Returns:
        List[Meeting]: a list of meetings
    """
    
    logger.info("trying to get all meetings")
    repository: Repository = get_repository()
    items = await repository.get({}, limit, offset)
    if items:
        return list(map(meeting_mongo_map, items))
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No elements in database found")


@REQUEST_TIME.time()
@router.get("/find/{field}/{value}", response_description="Find meetings by field", status_code=status.HTTP_200_OK, response_model=List[Meeting])
@caches(cache_meetings_find, "value")
async def find_meetings(field: str, value: str, response: Response) -> List[Meeting]:
    """_summary_

    Args:
        field (str): key to use on search
        value (str): value

    Raises:
        HTTPException: not found

    Returns:
        List[Meeting]: a list of meetings
    """
    if field == "id":
        field = "_id"
    if field == "people" and not re.match(".+\@.+", value):
        raise HTTPException(status_code = 400, detail="Bad request: input is email but doesn't match pattern")
    logger.info(f"searching elements with field {field} and value {value}")
    repository: Repository = get_repository()
    items = await repository.get({field: value}, 1000, 0)
    if items:
        return list(map(meeting_mongo_map, items))
    response.status_code = status.HTTP_404_NOT_FOUND
    return []


@REQUEST_TIME.time()
@router.get("/{id}", response_description="Get a meeting by its ID", status_code=status.HTTP_200_OK, response_model=Meeting)
@cached(cache_meetings_by_id)
async def find_meeting_by_id(id: str, response: Response) -> Meeting:
    """get a meeting by its id

    Args:
        id (str): id

    Raises:
        HTTPException: if not found

    Returns:
        Meeting: an element containing all the information of the meeting
    """
    logger.info(f"finding element by id {id}")
    repository: Repository = get_repository()
    item = await repository.get_by_id(id)
    if item:
        meeting = meeting_mongo_map(item)
        return meeting
    response.status_code = 404
    return {}

@REQUEST_TIME.time()
@router.post("/", response_description="Create a new meeting", status_code=status.HTTP_201_CREATED, response_model=GenericResponse)
async def save_meeting(meeting: Meeting) -> GenericResponse:
    """saves a meeting

    Args:
        meeting (Meeting): an element containing all the information of the meeting

    Raises:
        HTTPException: internal server error 500

    Returns:
        GenericResponse: a generic response with information about the operation
    """
    # if meeting.id is not None:
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="can't set a non null meeting_id")
    meeting.id = None
    logger.info("attempting to save " + meeting.json())
    repository: Repository = get_repository()
    try:
        res = await repository.insert(meeting.dict())
        logger.info(str(res))
        return GenericResponse(status=201, message=f"Created {res.inserted_id}", data=[meeting.dict()])
    except Exception as e:
        logger.error(e)
        logger.exception(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error saving meeting")
        

@REQUEST_TIME.time()
@router.put("/{id}", response_description="Update a meeting", status_code=status.HTTP_200_OK, response_model=GenericResponse)
async def update_meeting(id: str, data: Dict) -> GenericResponse:
    """updates a meeting

    Args:
        id (str): id
        data (Dict): json with key value pairs to be updated

    Raises:
        HTTPException: _description_

    Returns:
        Meeting: _description_
    """
    logger.info(f"updating element {id}")
    repository: Repository = get_repository()
    res = await repository.upsert(id, data)
    if res:
        return GenericResponse(status=200, message="Updated", data=[res])


def meeting_mongo_map(meeting):
    """just a mapper dict -> object mapper

    Args:
        meeting (_type_): _description_

    Returns:
        _type_: _description_
    """
    meeting = Meeting(
        id = str(meeting["_id"]),
        datetime_from = meeting["datetime_from"],
        datetime_to = meeting["datetime_to"],
        content = meeting["content"],
        people = meeting["people"],
        signatures = meeting["signatures"],
        subject = meeting["subject"]
    )
    return meeting


@REQUEST_TIME.time()
@router.delete("/{id}", response_description="Delete a meeting by its ID", status_code=status.HTTP_200_OK, response_model=GenericResponse)
async def delete_by_id(id: str) -> GenericResponse:
    """deletes a meeting

    Args:
        id (str): id

    Raises:
        HTTPException: a

    Returns:
        Meeting: GenericResponse
    """
    logger.info(f"deleting element {id}")
    repository: Repository = get_repository()
    item = await repository.get_by_id(id)
    if item:
        repository.delete(id)
        cache_meetings_by_id.popitem(id)
        return GenericResponse(status=200, message="deleted", data=[])
    return GenericResponse(status=404, message="not found", data=[])
    # res = await meetings_async.delete_one({"_id": ObjectId(id)})


@cachetools.cached({})
def get_repository():
    return Repository("demo_meetings")