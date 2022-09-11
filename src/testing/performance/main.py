from testing.performance.locustfiles.setup import setup
import gevent
from locust import HttpUser, task, between
from locust.env import Environment
from locust.stats import stats_printer, stats_history
from locust.log import setup_logging
from locustfiles.locustfile_scn01 import Scn01

from locust import main as locust_main

import locust

if __name__ == "__main__":
    # setup Environment and Runner
    locust_main.main()
    # env = Environment(user_classes=[Scn01])
    
    # # env.create_local_runner()
    # # web_ui = environment.create_web_ui(
    # #             host=web_host,
    # #             port=options.web_port,
    # #             auth_credentials=options.web_auth,
    # #             tls_cert=options.tls_cert,
    # #             tls_key=options.tls_key,
    # #             stats_csv_writer=stats_csv_writer,
    # #             delayed_start=True,
    # #             userclass_picker_is_active=options.class_picker,
    # #         )

    # # start a WebUI instance
    # env.create_local_runner()
    # env.create_web_ui(host="127.0.0.1", port=8089, delayed_start=True, userclass_picker_is_active=True)
    # env.web_ui.start()
    # setup()
    # env.web_ui.greenlet.join()

    # # start a greenlet that periodically outputs the current stats
    # gevent.spawn(stats_printer(env.stats))

    # # start a greenlet that save current stats to history
    # gevent.spawn(stats_history, env.runner)

    # # start the test
    # # env.runner.start(1, spawn_rate=10)

    # # in 60 seconds stop the runner
    # # gevent.spawn_later(60, lambda: env.runner.quit())

    # # wait for the greenlets
    # # env.runner.greenlet.join()
    # # env.web_ui.

    # # stop the web server for good measures
    # env.web_ui.stop()