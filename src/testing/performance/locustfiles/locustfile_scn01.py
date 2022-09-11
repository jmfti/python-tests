from json import JSONDecodeError
from random import random, randrange
import random
import locust
from locust import HttpUser, TaskSet, task, between, events, constant
import logging 
import dataclasses
from typing import Dict, List, Optional, Union 
import datetime
import logging
import json
import shelve
import time, datetime
import json
import re
import pymongo
import hashlib
import cachetools
from data_repository import SequentialDataProviderStrategy, RandomDataProviderStrategy, UniqueSequentialDataProviderStrategy



import sys
# import pymc3 as pm        # to compare 2 samples with pymc3 on a bayesian approach https://docs.pymc.io/en/v3/pymc-examples/examples/case_studies/BEST.html

@dataclasses.dataclass
class Meeting:
    datetime_from: datetime.datetime
    datetime_to: datetime.datetime 
    people: List[str]
    subject: str 
    content: str 
    signatures: List[str]
    id: Optional[str] = None


class Scn01(HttpUser):
    wait_time = constant(0.1)
    host = "http://app:5000"
    

    @task
    class CrudStresstest(TaskSet):
        config: dict
        logger: logging.Logger
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            config = None
            with open("/loadtest/config/config.json", "r") as fd:
                config = json.loads(fd.read())
            self.config = config
            self.gets_db = cachetools.TTLCache(2000, ttl=3600)
            self.logger = logging.getLogger(__name__)
            self.emails = RandomDataProviderStrategy(None, False, False)
            self.emails.from_csv(self.config["emails_path"])
            self.signatures = RandomDataProviderStrategy(None, False, False)
            self.signatures.from_csv(self.config["signatures_path"])
            
        
        def get_new_meeting(self) -> Meeting:
            people = [next(self.emails).email for i in range(random.randint(0, 7))]
            signatures = [next(self.signatures).signature for i in range(random.randint(0, 5))]
            new_meeting = {
                "datetime_from": datetime.datetime.now().replace(microsecond=0).isoformat(),
                "datetime_to": (datetime.datetime.now() + datetime.timedelta(hours=1)).replace(microsecond=0).isoformat(),
                "people": people,
                "subject": "test subject",
                "content": "test content",
                "signatures": signatures
            }
            return Meeting(**new_meeting)

        @task(2)
        def add_meeting(self):
            meeting_data = self.get_new_meeting()
            self.logger.info("adding new meeting")
            self.logger.info(dataclasses.asdict(meeting_data))
            with self.client.post("/meetings/", json=dataclasses.asdict(meeting_data), catch_response=True) as response:
                self.logger.info(f"""
POST /meetings
request
-----------------
{json.dumps(dataclasses.asdict(meeting_data))}

response
-----------------
{str(response.headers)}
{json.dumps(response.text)}
                            """)
                try:
                    id = re.findall("Created (.*)", response.json()["message"])[0] 
                    if not re.match("\w{4,}",id):
                        response.failure("bad_id")
                    self.logger.info(f"adding new entry to cache {id}")
                    self.gets_db[id] = id
                    # self.gets_db.sync()
                    #self.logger.info(str(self.gets_db.items()))
                except JSONDecodeError as e:
                    self.logger.exception("looks like failed to create a meeting")
                    response.failure("json decode failed")
                finally:
                    self.wait()
                
                
                

        @task(1)
        def find_meeting(self):
            additional_people = [random.randint(0,1000) for i in range(random.randint(1,4))]
            people = [f"{i}@company.com" for i in additional_people]
            person = random.choice(people)
            self.logger.info("trying to get " + f"/meetings/find/people/{person}")
            with self.client.get(f"/meetings/find/people/{person}", catch_response=True, name="/meetings/find/people/{email}") as response:
                self.logger.info(response.text)
                try:
                    # json_data = response.json()
                    a = 0
                except JSONDecodeError as e:
                    self.logger.info(e.msg)
                    self.logger.info(e.lineno)
                    self.logger.exception("failed decoding json")
                    # e.with_traceback()
                finally:
                    self.wait()
                    
        @task(1)
        def get_meeting(self):
            if len(list(self.gets_db.keys())) > 0:
                id = random.choice(list(self.gets_db.keys()))
            else:
                id = hashlib.md5(str(time.time()).encode("utf8")).hexdigest()
            with self.client.get(f"/meetings/{id}", catch_response=True, name="/meetings/{id}") as response:
                self.logger.info(response.text)
                
            self.wait()
        
            
            