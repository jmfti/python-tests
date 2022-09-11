from dataclasses import dataclass
from typing import Dict, List, Optional, Union 
import motor.motor_asyncio
import datetime
import json
import hashlib
from pydantic import BaseModel
import pprint
import fastapi 
from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
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
    meetings_cursor = meetings_async.find().limit(limit).skip(offset)
    meetings_list = await meetings_cursor.to_list(limit)
    lista = list(map(meeting_mongo_map, meetings_list))#[meeting_mongo_map(i) for i in meetings_list]
    if len(lista) == 0:
        raise HTTPException(status_code=404, detail="No elements in database")
    return lista

@REQUEST_TIME.time()
@router.get("/find/{field}/{value}", response_description="Find meetings by field", status_code=status.HTTP_200_OK, response_model=List[Meeting])
@caches(cache_meetings_find, "value")
async def find_meetings(field: str, value: str) -> GenericResponse:
    """_summary_

    Args:
        field (str): key to use on search
        value (str): value

    Raises:
        HTTPException: not found

    Returns:
        List[Meeting]: list of meetings
    """
    logger.info(f"searching elements with field {field} and value {value}")
    if field == "id":
        field = "_id"
    if field == "people" and not re.match(".+\@.+", value):
        raise HTTPException(status_code = 400, detail="Bad request: input is email but doesn't match pattern")
    data = await meetings_async.find({
        field: { "$in": [value] }
    }).to_list(length=1000)
    if len(data) == 0:
        raise HTTPException(status_code = 404, detail="No elements in database")
    logger.info(str(data[0]['people']))
    return list(map(meeting_mongo_map, data))

@REQUEST_TIME.time()
@router.get("/{id}", response_description="Get a meeting by its ID", status_code=status.HTTP_200_OK, response_model=Meeting)
@cached(cache_meetings_by_id)
async def find_meeting_by_id(id: str) -> Meeting:
    """get a meeting by its id

    Args:
        id (str): id

    Raises:
        HTTPException: if not found

    Returns:
        Meeting: an element containing all the information of the meeting
    """
    logger.info(f"finding element by id {id}")
    data = await meetings_async.find_one({"_id": ObjectId(id)})
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if "id" in data:
        data["id"] = str(data["id"])
    meeting: Meeting = meeting_mongo_map(data)
    logger.info(f"found {meeting.json()}")
    return meeting

@REQUEST_TIME.time()
@router.post("/", response_description="Create a new meeting", status_code=status.HTTP_201_CREATED, response_model=GenericResponse)
async def save_meeting(meeting: Meeting) -> GenericResponse:
    """saves a meeting

    Args:
        meeting (Meeting): _description_

    Raises:
        HTTPException: _description_

    Returns:
        Dict: _description_
    """
    # if meeting.id is not None:
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="can't set a non null meeting_id")
    meeting.id = None
    logger.info("attempting to save " + meeting.json())
    
    data = None
    try:
        data = meeting.dict()
        logger.info(f"attempting to save {meeting.json()}")
        res = await meetings_async.insert_one(data)
        id = str(res.inserted_id)
        response = GenericResponse(status=200, message=f"Created {id}", data=[])
        return response
    except Exception as e:
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{str(e)}")

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
    meeting_orig: Meeting = await meetings_async.find_one({"_id": ObjectId(id)})
    
    if meeting_orig is None:
        raise HTTPException(status_code=404, detail="Meeting not found")
    await meetings_async.update_one({"_id": id}, {"$set": data})
    response = GenericResponse(status=200, message="Updated", data=[])


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
    logger.info(f"deleting element {id}")
    res = await meetings_async.delete_one({"_id": ObjectId(id)})
    return GenericResponse(status=200, message="deleted", data=[])