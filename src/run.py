#!/bin/env/python
# -*- coding:utf-8 -*-

import os
import sys
import glob
import signal
import logging
from tornado.options import define, options

from daemon import Daemon
from main_server import start_server
from main_server import stop_server as stop_tornado

CUR_DIR = os.path.split(os.path.realpath(__file__))[0]

class Server(Daemon):
    def __init__(self, port):
        super(Server, self).__init__(os.path.join(CUR_DIR, "../server.%d.pid" % port),
                                     stderr_name = "stderr.%d" % port,
                                     stdout_name = "stdout.%d" % port)
        self.port = port

    def _register_signal_handler(self):
        def sigterm_handler(signum, frame):
            logging.info("receive signal %d. will stop now" % signum)
            self.stop_server()
        signal.signal(signal.SIGTERM, sigterm_handler)
        signal.signal(signal.SIGINT, sigterm_handler)

    def stop_server(self):
        stop_tornado()
        exit(0)

    def start_server(self):
        self._register_signal_handler()
        self.start()

    def run(self):
        start_server(self.port)

define("port", 5004, help="Server listen port", type = int)
define("stop", False, help="Stop server on ${port}", type = bool)

if __name__ == "__main__":
    options.parse_command_line()
    port = options.port
    server = Server(port)
    if options.stop:
        server.stop()
    else:
        server.start_server()
