# README
This is a full stack python rest service monitored with grafana and prometheus, automated functional test with pytest, performance test with locust, database mongo
It shows examples of generating metrics, an implementation of state design pattern, handling startup events of locust, use of cachetools with fastapi to create monitored caches (which adds up to prometheus metrics exporter). Test data management in locust with custom data samplers, modified html report to include a kolmogorov smirnov test to test whether there's a significative difference between samples of baseline and current run. Hooked the report generation to embed a table with main response times of the baseline run (for every generated report)

==FastAPI==
* a state patter design example in metrics_controller
* a prometheus monitored cache that inherits from cachetools.TTLCache to gather metrics of hits and miss

next steps
* move crud logic to a repository

Grafana has a personalized dashboard for performance testing.

Locust has hooks on events startup and stop to gather statistics and send email, comparing results of 2 runs with a baseline setted in the config file. It gathers metrics while test is running, it stores these metrics in sqlite. It's HDD dependant, can bottleneck throughput of load generators.
Next should be: 

* try to hook web_ui to modify the web ui and add a dynamic pacing configuration
* store metrics in memory and write on a separate thread every X elements

next steps
* add network and disk metrics



what's in the docker stack
* the rest service on port 81 and 90 on host. 5000 and 8000 in container
* mongo db for the rest service, port 27017
* automatic functional test with pytest
* master node for locust on 8089 with web ui
* load injectors (worker nodes)
* prometheus with scrapers to get metrics
* grafana with personalized dashboard with performance custom metrics on port 3000 on host
* locust metrics exporter


next things to add? selenium... a more complex rest api...