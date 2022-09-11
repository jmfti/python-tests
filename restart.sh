#!/bin/bash

docker service scale pruebaPython_loadtests-master=0
docker service scale pruebaPython_loadtests-worker=0

docker service scale pruebaPython_loadtests-worker=4
docker service scale pruebaPython_loadtests-master=1