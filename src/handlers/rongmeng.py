# coding: utf-8
import logging
import os
import json

import tornado.web
import tornado.gen
import hashlib
import words

from model.order_model import ThirdPayOrders
from model.table_base import Wanted

CUR_PATH = os.path.split(os.path.realpath(__file__))[0]

member_year = "365"
member_forever = "36500"
year_num = 2900
forever_num = 5900


# Rong Meng pay call back handler.
class RongmengNotifyHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self):
        order = ThirdPayOrders()
        order.stat = self.get_argument("return_code")
        order.price = int(self.get_argument("totalFee"))
        order.order_id = self.get_argument("channelOrderId")
        order.trans_id = self.get_argument('orderId')
        ts = self.get_argument('timeStamp')
        sign = self.get_argument('sign')
        if not self.check_sign(order.order_id, order.trans_id, ts, order.price, sign):
            self.write('FAIL')
            return
        self.parse_ext_param(self.get_argument('attach'), order)
        order.tag = words.RongMengTag
        order.success = True
        order.ext = '{{"3rd_trans_id": {0},"pay_time": {1}}}'.format(self.get_argument("transactionId"), ts)
        db_order = yield tornado.gen.Task(ThirdPayOrders.get_one, order.order_id)
        if db_order:
            if not db_order.success:
                new_order = db_order()
                new_order.order_id = order.order_id
                new_order.stat = order.stat
                new_order.success = True
                new_order.update_to_db()
        else:
            order.visible = self.settings['server_conf'].may_deduct(order.channel)
            order.save()
        self.write("SUCCESS")

    def parse_ext_param(self, ext_str, order):
        attach = ext_str.split(',')
        if len(attach) > 3:
            order.channel = attach[0]
            order.uid = attach[1]
            order.product = attach[2]
            order.pkg = attach[3]
        else:
            attach = ext_str.split('.')
            if len(attach) == 1:
                order.channel = 'OldVer'
                order.uid = attach[0]
                order.product = 'Unknown'
                return
            order.channel = attach[0]
            order.uid = attach[1]
            if len(attach) > 3:
                order.product = attach[2]
                order.pkg = attach[3]
            elif len(attach) > 2:
                order.product = attach[2]

    def check_sign(self, order_id, tans_id, ts, price, sign):
        str_to_sign = 'channelOrderId={0}&orderId={1}&timeStamp={2}&totalFee={3}'.format(
            order_id, tans_id, ts, price
        )
        return hashlib.md5(str_to_sign).hexdigest() == sign


class RongmengPayStatQueryHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        uid = self.get_argument('uuid')
        order_id = self.get_argument('channelOrderId')
        db_order = ThirdPayOrders()
        db_order.order_id = order_id
        db_order.uid = Wanted
        db_order.tag = Wanted
        db_order.success = Wanted
        ret = yield tornado.gen.Task(db_order.update_from_db)
        if not ret:
            self.write('FAIL')
        elif db_order.tag != words.RongMengTag or not db_order.success:
            self.write('FAIL')
        else:
            self.write('SUCCESS')


class RongmengQueryHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        uid = self.get_argument('uuid')
        success, db_orders = yield tornado.gen.Task(ThirdPayOrders.get_some, 'uid="{}"'.format(uid))
        ans = ''
        if success:
            for db_order in db_orders:
                if db_order.tag != words.RongMengTag or not db_order.success or ans == member_forever:
                    continue
                if db_order.price == year_num:
                    ans = member_year
                elif db_order.price > year_num:
                    ans = member_forever
        self.write(ans)
