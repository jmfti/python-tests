#!/usr/bin/bash

cd images/python 
docker build -f GeneratorDocker -t python-pyagrum .
cd ../../


docker run -v $(pwd)/output:/output -v $(pwd)/input:/input -v $(pwd)/src/testing/performance/testdata:/app python-pyagrum python /app/testdata_generator.py --input /input/log.txt --output /output