# coding: utf-8
import json
import logging
import os
import urllib2

import tornado.web

from model.order_model import OrderModel
from util_tools import des_decoder, des_encoder, simple_cache

CUR_PATH = os.path.split(os.path.realpath(__file__))[0]


class Mimi2Handler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def post(self):
        paramMap = self.get_argument("paramMap")
        paramMap = urllib2.unquote(paramMap)
        logging.info("paramMap:%s" % paramMap)
        obj = json.loads(paramMap)

        tag = int(obj['actionName'])
        if tag == 1:
            self.write(self.file_get_contents("1.txt"))
        elif tag == 2:
            self.write(self.file_get_contents("2.txt"))
        elif tag == 3:
            self.write(self.file_get_contents("list/%s.txt" % obj['specialId']))
        elif tag == 4:
            self.write(self.file_get_contents("film/%s.txt" % obj['filmId']))
        elif tag == 5:
            self.write(self.file_get_contents("ad.txt"))
        self.finish()

    @simple_cache(expired_time=30)
    def file_get_contents(self, fname):
        ctnt = "Error"
        fpath = os.path.join(CUR_PATH, "../w0", fname)
        logging.info("Get file [%s] content." % fpath)
        with open(fpath) as f:
            ctnt = f.read()
        return ctnt


class Mimi2CallbackHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def post(self):
        rsp = self.get_argument("callback_rsp")
        user = self.get_argument("callback_user")
        appkey = self.get_argument("callback_appkey")

        logging.debug("rsp:[%s]" % rsp)
        logging.debug("user:[%s]" % user)
        logging.debug("appkey:[%s]" % appkey)

        rsp_str = des_decoder(rsp, key='H74S0Dd2')
        usr_str = des_decoder(user, key='H74S0Dd2')

        rsp_obj = self._decode(rsp_str)
        usr_obj = self._decode(usr_str, '#')
        appkey_decode = des_decoder(rsp, key='2SoXIhFB')

        logging.debug("rsp_obj:%s" % rsp_obj)
        logging.debug("usr_obj:%s" % usr_obj)

        od = OrderModel(self.settings["db_inst"])
        od.initFromObj(usr_obj)
        od.initFromObj(rsp_obj)

        if od.isDuplicate():
            logging.info("Recieve duplicate order id.%s" % od.order_id)
            self.finish()
            return
        od.add()
        self.write("1")
        self.finish()

        # [(key, val), (key, val)]

    def _decode(self, s, seq='&'):
        ret = {}
        for item in ((i[:i.find('=')], i[i.find('=') + 1:]) for i in s.split(seq)):
            ret[item[0].strip()] = item[1]
        return ret

    def _md5(self, tar):
        fields = ['app_key', 'txn_seq', 'order_id', 'rsp_code',
                  'txn_time', 'actual_txn_amt', 'time_stamp']


class Mimi2UserHandler(tornado.web.RequestHandler):
    member_year = "%s:365"
    member_forever = "%s:36500"
    year_num = 2900
    forever_num = 5900
    encrypt_key = "Cx29uPa7"

    @tornado.web.asynchronous
    def post(self):
        uid = self.get_argument("uid")
        od = OrderModel(self.settings["db_inst"])
        od.setUid(uid)

        money = od.getPayed()
        logging.info("user [%s] money [%s]" % (uid, money))
        if money == self.year_num:
            self.write(des_encoder(bytes(self.member_year % uid), self.encrypt_key))
        elif money == self.forever_num:
            self.write(des_encoder(bytes(self.member_forever % uid), self.encrypt_key))
        self.finish()


class Mimi2QueryOrderHandler(tornado.web.RequestHandler):
    rsp_format = "%s:%s"
    encrypt_key = "Cx29uPa7"

    @tornado.web.asynchronous
    def post(self):
        order_id = self.get_argument("order_id")
        od = OrderModel(self.settings["db_inst"])
        od.setOrderId(order_id)

        status = od.getOrderStatus()
        logging.info("order [%s] status [%s]" % (order_id, status))
        if status is not None:
            self.write(des_encoder(bytes(self.rsp_format % (order_id, status)), self.encrypt_key))
        else:
            self.write(des_encoder(bytes(self.rsp_format % (order_id, "Unknow")), self.encrypt_key))
        self.finish()
