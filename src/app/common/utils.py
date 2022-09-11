import logging, os
from config import get_config
import motor.motor_asyncio
from typing import Dict
import pymongo
from bson.objectid import ObjectId



cfg = get_config()

def get_logger(name:str):
    """Configures the logging module, and returns it

    Writes to a file log, also outputs it in the console
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    fh = logging.FileHandler("../python_app.log")
    fh.setLevel(logging.DEBUG)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    # create formatter and add it to the handlers
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


def read_docker_secret(name: str) -> str:
    """
    Read a secret by name from as a docker configuration

    :param name: name of the secret
    :return: the secret as a string
    """
    with open(os.environ.get(name), "r") as file:
        return file.read()


class Repository:
    def __init__(self, collection: str):
        cfg: Dict = get_config()
        self.__db = motor.motor_asyncio.AsyncIOMotorClient(host=cfg.get("mongo_host"), port=cfg.get("mongo_port"))[collection]#pymongo.MongoClient(host=cfg.get("mongo_host"), port=cfg.get("mongo_port"))[collection]

    async def get(self, query: dict, limit: int = 10, offset: int = 0):
        res = await self.__db.find(query).limit(limit).skip(offset)
        return list(res)
    
    async def get_by_id(self, id: str):
        res = await self.__db.find_one({"_id": ObjectId(id)})
        return res

    async def upsert(self, key, data: dict):
        return await self.__db.update_one(
            {"_id": key}, {"$set": data}, upsert=True
        )


    async def delete(self, key):
        return await self.__db.delete_one({"_id": key})

    async def delete_many(self, index=None, key=None):
        if index and key:
            return await self.__db.delete_many({index: key})
        else:
            return await self.__db.delete_many({})

    async def drop(self):
        return await self.__db.drop()