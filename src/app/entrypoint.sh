#!/usr/bin/env sh

# make shit to automate 

# get url to download from env passed by the docker stack
# in production clone 
#git clone https://source/repositories/${ENV_APP_NAME}

#pip install -qr /app/requirements.txt
echo "Executing ${ENV_APP_NAME}.py with args ${ENV_APP_ARGS}"
LOGLEVEL="error"
if [ "${ENVIRONMENT}" = "DEV" ]; then
    LOGLEVEL="debug"
    # do other things? if dev better to mock db? dev -> mock & pre -> db?
fi
#echo "gunicorn -w 2 -k uvicorn.workers.UvicornH11Worker --chdir /app --bind 0.0.0.0:5000 --log-level ${LOGLEVEL} ${ENV_APP_NAME}:app"
gunicorn -w 2 -k uvicorn.workers.UvicornH11Worker --workers ${WORKERS} --reload-engine auto --chdir /app --bind 0.0.0.0:5000 --log-level ${LOGLEVEL} ${ENV_APP_NAME}:app
#python /app/${ENV_APP_NAME}.py ${ENV_APP_ARGS}