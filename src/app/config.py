import json
import logging

logger = logging.getLogger(__name__)

def get_config():
    with open("./app_config.json", "r") as fd:
        config = json.loads(fd.read())
        logger.info(f"config loaded: {json.dumps(config)}")
        return config
        