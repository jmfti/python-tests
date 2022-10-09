import random
from tokenize import Double
import locust
from locust import events
import logging 
from typing import Dict, List, Optional, Union 
import datetime
import json
import sqlite3
import time, datetime
import pandas as pd
import json
import re
import smtplib
from email.mime.text import MIMEText
import pymongo

import gevent
from locust import HttpUser, task, between
from locust.env import Environment
from locust.stats import stats_printer, stats_history, StatsCSV, StatsCSVFileWriter
from locust.log import setup_logging
import locust.html
import pyquery
import scipy.stats
import csv
import requests


setup_logging("INFO", None)

config = None
with open("/loadtest/config/config.json", "r") as fd:
    config = json.loads(fd.read())
    
con: sqlite3.Connection = None
logger = logging.getLogger()
ch = logging.StreamHandler()
formatter = logging.Formatter('%(relativeCreated)6d %(asctime)s %(module)s.%(funcName)s %(lineno)s %(message)s')
con = sqlite3.connect(config["session_db"])  # performance degrading. should give a try to redis
session_data = {}
meetings_db = pymongo.MongoClient("mongo", 27017).demo.meetings

# logging.basicConfig(level=logger.info, format='%(relativeCreated)6d %(asctime)s %(module)s.%(funcName)s %(lineno)s %(message)s')
logger.setLevel(logging.INFO)
ch.setLevel(logging.INFO)
ch.setFormatter(formatter)
logger.addHandler(ch)

############# just a hack to test if report can be modified to my needs ############
from locust import html 
orig_render_template = html.render_template 
def render_template_replace(file, **kwargs):
    # just a hack to try to render a new html report
    logger.info(file)
    return orig_render_template(file, **kwargs)
# html.render_template = render_template_replace    # hook render_template calls to modify behavior. Change html and pass more data to the view
logger.info("######################################  registering hooks #######################################")
# logger.info("#"*1500)

@events.init.add_listener
def _(environment, **_kwargs):
    # prepare test data, check infrastructure status, ...
    logger.info("2. Initializing locust, happens after parsing the locustfile but before test start")


@events.quitting.add_listener
def _(environment, **_kwargs):
    logger.info("9. locust is shutting down")

#on test start remove any previous info and prepare for new session data
@events.test_start.add_listener
def _(environment, **_kwargs):
    """happens only once in headless runs, but can happen multiple times in web ui-runs"""
    global con, session_data
    logger.info("3. Starting test run")
    start_time = datetime.datetime.now()
    session_data["start_time_string"] = start_time.strftime('%Y%m%d_%H%M%S')
    session_data["start_datetime"] = start_time
    cur = con.cursor()
    if environment.web_ui:
        # if exists session_default remove it and create a new one
        cur.execute("drop table if exists session_default;")
        con.commit()
        cur.execute("create table session_default (request_type text, name text, response_time REAL, response_length INTEGER, error_msg text, context text);")
        con.commit()
    # query db, find all articles, ... get test data


@events.quit.add_listener
def _(environment, exit_code, **kwargs):
    logger.info(f"10. Locust has shut down with code {exit_code}")


@events.test_stopping.add_listener
def _(environment, **_kwargs):
    logger.info("6. stopping test run")

    

# on test stop save data in other table and clean
@events.test_stop.add_listener
def on_test_stop(environment, **_kwargs):
    if environment.web_ui:
        # if master rename session table and delete session_default
        global con, session_data
        if session_data['start_time_string'] == datetime.datetime.now().strftime("%Y%m%d_%H%M%S"):
            return
        cur = con.cursor() 
        # don't know why sometimes the test starts 2 times and it throws an exception
        cur.execute(f"drop table if exists session_{session_data['start_time_string']}")
        # persist data in its final table 
        cur.execute(f"create table session_{session_data['start_time_string']} as select * from session_default;")
        con.commit()
        # this should be moved to SessionService.saveSession
        # once session is saved we should get the differences (SessionService.summarizeDifferences)
        # once we got the differences between 2 runs -> compose email with results and send to config['reportee']
        session_string = session_data['start_time_string']
        df_a = pd.read_sql_query(f"select * from session_{config['baseline']}", con)
        df_b = pd.read_sql_query(f"select * from session_default", con)
        logger.info(df_a.head(5).to_markdown())
        runs = {
            session_string: {},
            "default": {}
        }
        runs["default"]["response_times"] = pd.DataFrame()
        quantiles = (0.275, 0.5, 0.9, 0.95, 0.975, 0.99)
        for quant in quantiles:
            runs["default"]["response_times"][f"response_times_{quant}"] = df_b.groupby("name").quantile(quant).response_time
        
        runs["default"]["response_times"]["response_times_avg"] = df_b.groupby("name").mean().response_time
        runs["default"]["response_times"]["response_times_var"] = df_b.groupby("name").var().response_time
        runs["default"]["response_times"]["response_times_std"] = df_b.groupby("name").std().response_time
        
        runs[session_string]["response_times"] = pd.DataFrame()
        for quant in quantiles:
            runs[session_string]["response_times"][f"response_times_{quant}"] = df_a.groupby("name").quantile(quant).response_time
        
        runs[session_string]["response_times"]["response_times_avg"] = df_a.groupby("name").mean().response_time
        runs[session_string]["response_times"]["response_times_var"] = df_a.groupby("name").var().response_time
        runs[session_string]["response_times"]["response_times_std"] = df_a.groupby("name").std().response_time
        
        message = f"""
Test A: {session_string}
Test B: last

response times for test {session_string}
-------------------------
{runs['default']['response_times'].to_markdown()}

response times for last test 
-------------------------
{runs[session_string]['response_times'].to_markdown()}
        """
        msg = MIMEText(message)
        msg["To"] = config["reportee"]
        msg["Subject"] = config["subject"]
        msg["From"] = config["from"]
        logger.info(f"trying to connect to {config['smtp_server']} on port {config['smtp_port']}")
        try:
            s = smtplib.SMTP(config["smtp_server"], config["smtp_port"])
            s.sendmail(config['from'], [config["reportee"]], msg.as_string())
            s.quit()
        except Exception as ex:
            with open("/output/failed_mail.txt", "w") as fd:
                fd.write(message)
                
        
        html_report = locust.html.get_html_report(environment)
        with open("/output/html_report.html", "w") as fd:
            fd.write(html_report)
        baseline_table = df_a.groupby("name").mean().to_html(classes="stats")
        
        res = {}
        for name in df_a.name.unique():
            sample_a = df_a.query(f"name == '{name}'").response_time
            if not name in df_b.name.unique():
                continue
            sample_b = df_b.query(f"name == '{name}'").response_time
            result = scipy.stats.ks_2samp(sample_a, sample_b)
            res[name] = result.pvalue
        
        new_panel = f"""<div id=\"added_info\"><h1>Baseline run data for comparison</h1>{baseline_table}<br>
        Kolmogorov smirnov test results<br>"""
        for key in res:
            logger.info(res[key])
            # if type(res[key]) != type(float(0.05)):
            #     continue
            new_panel += f"differences in response times in uri {key} are {'not' if res[key] > 0.05 else ''} signifficant <br>" #reject null hypothesis (both samples equal) if p < 0.05, samples differ if p < 0.05
        new_panel += "</div>"
        with open("/output/html_report_extended.html", "w") as fd:
            fd.write(html_report.replace("""<div id="tasks">""", f"""{new_panel}<div id="tasks">"""))
        
        # try to get the csv data from locust
        # make an http request to http://app:5000/stats/requests/csv and save it to /output/requests.csv
        data = requests.Session().get("http://app:5000/stats/requests/csv").text
        with open("/output/requests.csv", "w") as fd:
            fd.write(data)

    logger.info("8. test run stopped")
    


@events.init.add_listener
def locust_init(environment, **kwargs):
    """
    This gets executed when locust initializes
    """
    global con
    if environment.web_ui:
        @environment.web_ui.app.route("/data_csv/<session_string>")
        def get_data_csv(session_string : str):
            """
            Add a route to the Locust web app, where we can see the total content-length
            """
            if re.match("\d{8}_\d{6}", session_string):
                return pd.read_sql_query(f"select * from session_{session_string}", con).to_csv()
        
        @environment.web_ui.app.route("/fire_on_stop")
        def fire_on_stop():
            on_test_stop(environment, **kwargs)
        

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, context, **kwargs):
    """
    Event handler that get triggered on every request.
    """
    global con
    cur = con.cursor()
    logger.info("inserting values " + str(tuple([request_type, name, response_time, response_length, "ksdnfakjsnf", json.dumps(context)])))
    res = cur.execute("""insert into session_default (request_type, name, response_time, response_length, error_msg, context) values (?, ?, ?, ?, ?, ?) """, (request_type, name, response_time, response_length, "ksdnfakjsnf", json.dumps(context)))
    res = con.commit()
    logger.info(json.dumps(res))
    
    

@events.report_to_master.add_listener
def on_report_to_master(client_id, data):
    """
    This event is triggered on the worker instances every time a stats report is
    to be sent to the locust master. 
    """
    data["random_metric"] = random.randint(0,59) # send a random metric to see if it gets reported
    return

@events.worker_report.add_listener
def on_worker_report(client_id, data):
    """
    This event is triggered on the master instance when a new stats report arrives
    from a worker. 
    """
    return


# if __name__ == "__main__":
#     # setup Environment and Runner
#     env = Environment(user_classes=[Scn01])
    
#     # env.create_local_runner()

#     # start a WebUI instance
#     env.create_local_runner()
#     env.create_web_ui("127.0.0.1", 8089)
#     env.web_ui.greenlet.join()

#     # start a greenlet that periodically outputs the current stats
#     gevent.spawn(stats_printer(env.stats))

#     # start a greenlet that save current stats to history
#     gevent.spawn(stats_history, env.runner)

#     # start the test
#     # env.runner.start(1, spawn_rate=10)

#     # in 60 seconds stop the runner
#     # gevent.spawn_later(60, lambda: env.runner.quit())

#     # wait for the greenlets
#     # env.runner.greenlet.join()
#     # env.web_ui.

#     # stop the web server for good measures
#     env.web_ui.stop()