#!/usr/bin/bash
# TODO: get rid of this. No need to spawn a process for this. https://fastapi.tiangolo.com/advanced/events/
# just create the thread 
# just test if app is up and running
test_app() {
    RESPONSE=$(curl --silent http://app:5000/metrics_generator/status 2>/dev/null | grep document)
    echo "${RESPONSE}"
    if [[ $RESPONSE =~ on|off ]]
    then
        return true
    else
        return false
    fi
}

while [ true ]
do 
    if [ test_app ] #if application is already up and running
    then 
        curl -v --silent http://app:5000/metrics_generator/status/true  # activate the metrics generator just to show how to register metrics for prometheus
        sleep 5
        break
    else 
        echo "not matches, retrying"
        sleep 3
    fi
done

# start listening in port 8000 for metrics requests
curl -v --silent http://app:5000/metrics_generator/activate_new_thread


# sleep 10
# while [ true ]
# do 
#     set RESPONSE = curl -v --silent http://app:5000/metrics_management/status 2>&1 | grep activated
#     sleep 3 
# done