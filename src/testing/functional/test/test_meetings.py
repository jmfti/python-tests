
import pytest
import requests
import json
from utils import Collection
from typing import Generator
import datetime
import pprint
import logging
import re

logger = logging.getLogger(__name__)

host = "http://app:5000"
headers = {"accept": "application/json", "Content-Type": "application/json"}

print(f"test_meetings name -> {__name__}")


@pytest.fixture
def meetings(demo_db) -> Generator[Collection, None, None]:
    collection = Collection(demo_db, "meetings")
    yield collection
    collection.drop()


def test_create_meeting(meetings):
    new_meeting = {
        "datetime_from": datetime.datetime.now().replace(microsecond=0).isoformat(),
        "datetime_to": (datetime.datetime.now() + datetime.timedelta(hours=1)).replace(microsecond=0).isoformat(),
        "people": ["asjnd@and9nas.asdjn", "nda9nsd@as9dnad.asd"],
        "subject": "test subject",
        "content": "test content",
        "signatures": ["snf9nas9unsdf", "ndas9dna9s8dn", "das7bd8bddb"]
    }
    print("creating new meeting")
    pprint.pprint(new_meeting)
    
    response = requests.post(
        url=f"{host}/meetings",
        headers=headers,
        data=json.dumps(new_meeting)
    )
    logger.info(f"{json.dumps(response.json())}")
    
    assert response.status_code == 201
    data = response.json()
    pprint.pprint(data)
    # assert data["datetime_from"] == new_meeting["datetime_from"]
    assert "Created" in data["message"]
    
def test_find_meeting(meetings):
    
    new_meeting = {
        "datetime_from": datetime.datetime.now().replace(microsecond=0).isoformat(),
        "datetime_to": (datetime.datetime.now() + datetime.timedelta(hours=1)).replace(microsecond=0).isoformat(),
        "people": ["asjnd@and9nas.asdjn", "nda9nsd@as9dnad.asd"],
        "subject": "test subject",
        "content": "test content",
        "signatures": ["snf9nas9unsdf", "ndas9dna9s8dn", "das7bd8bddb"]
    }
    
    response = requests.post(
        url=f"{host}/meetings",
        headers=headers,
        data=json.dumps(new_meeting)
    )
    data = response.json()
    assert "Created" in data["message"]
    id = extract_id(data["message"])
    
    response = requests.get(f"{host}/meetings/{id}", headers=headers)
    
    data = response.json()
    assert response.status_code == 200
    assert id == data["id"]
    
    

def test_delete_meeting(meetings):
    
    new_meeting = {
        "datetime_from": datetime.datetime.now().replace(microsecond=0).isoformat(),
        "datetime_to": (datetime.datetime.now() + datetime.timedelta(hours=1)).replace(microsecond=0).isoformat(),
        "people": ["asjnd@and9nas.asdjn", "nda9nsd@as9dnad.asd"],
        "subject": "test subject",
        "content": "test content",
        "signatures": ["snf9nas9unsdf", "ndas9dna9s8dn", "das7bd8bddb"]
    }
    
    response = requests.post(
        url=f"{host}/meetings",
        headers=headers,
        data=json.dumps(new_meeting)
    )
    data = response.json()
    assert "Created" in data["message"]
    id = extract_id(data["message"])
    
    response = requests.delete(f"{host}/meetings/{id}", headers=headers)
    data = response.json()
    assert response.status_code == 200
    
    response = requests.get(f"{host}/meetings/{id}")
    data = response.json()
    assert response.status_code == 404
    assert data["detail"] == "Not found"
    
    # assert requests.delete(f"{host}/meetings/ksdfjnaskjfnsa", headers=headers).status_code == 404
    

def extract_id(msg):
    return re.findall("Created (.*)", msg)[0]

# include some tests to see expected behavior relative to 
# input format -> if we send bad format it should respond with bad request
# test requests for each parameter with extreme values 
# on array inputs try to send null, array with zero elements, 1 and 1000