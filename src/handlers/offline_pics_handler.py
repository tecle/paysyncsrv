# coding: utf-8
import json
import logging
import os
import urllib2

import tornado.web

from util_tools import simple_cache

CUR_PATH = os.path.split(os.path.realpath(__file__))[0]


class GetPicsHandler(tornado.web.RequestHandler):
    file_cache = {}
    expire_time = 10

    @tornado.web.asynchronous
    def post(self):
        paramMap = self.get_argument("paramMap")
        paramMap = urllib2.unquote(paramMap)
        obj = json.loads(paramMap)
        logging.debug("obj:%s" % paramMap)

        tag = obj['ptype']
        self.write(self.file_get_contents("%s.txt" % tag))
        self.finish()

    @simple_cache(expired_time=10)
    def file_get_contents(self, fname):
        ctnt = "Error"
        fpath = os.path.join(CUR_PATH, "../w1", fname)
        logging.info("Get file [%s] content." % fpath)
        with open(fpath) as f:
            ctnt = f.read()
        return ctnt
