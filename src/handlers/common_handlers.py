# coding: utf-8

import json
import words
import logging

import tornado.web
import tornado.gen

from model.table_base import Wanted
from model.order_model import ThirdPayOrders
from handlers.rongmeng import RongmengNotifyHandler
from handlers.fafapay_handler import FfCallbackHandler
from util_tools import gen_order_id


class GetUserOrdersHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        uid = self.get_argument('uid', None)
        channel = self.get_argument('cid', None)
        start = self.get_argument('start', 0)
        size = int(self.get_argument('num', 20))
        size = min(20, size)
        cond = 'success=1 {0} {1} order by create_time desc limit {2},{3}' \
            .format('and uid="{}"'.format(uid) if uid else '', 'and channel="{}"'.format(channel) if channel else '',
                    start, size)
        logging.info(cond)
        success, db_orders = yield tornado.gen.Task(ThirdPayOrders.get_some, cond)
        ans = []
        if success:
            for db_order in db_orders:
                ans.append({
                    'channel': db_order.channel,
                    'user': db_order.uid,
                    'price': db_order.price,
                    'oid': db_order.order_id,
                    'product': db_order.product,
                    'time': db_order.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                })
        self.write(json.dumps(ans, indent=2))


class GetOrderInfoHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        order = ThirdPayOrders()
        order.order_id = self.get_argument('oid')
        order.success = Wanted
        order.price = Wanted
        order.channel = Wanted
        logging.info('query order:[{}]'.format(order.order_id))
        res = yield tornado.gen.Task(order.update_from_db)
        if not res:
            self.write('{"code":202, "msg": "order not exist.", "price":0, "channel": ""}')
        elif order.success:
            self.write('{{"code":200, "msg":"", "price":{}, "channel":"{}"}}'.format(order.price, order.channel))
        else:
            self.write('{"code":203, "msg": "order not success.", "price":0, "channel": ""}')


class PrepayHandler(tornado.web.RequestHandler):
    __rt_cache__ = {}

    @tornado.web.asynchronous
    def post(self):
        uid = self.get_argument('uid')
        cid = self.get_argument('cid')
        price = int(self.get_argument('price'))  # 单位分
        sdk = self.get_argument('sdk')
        pkg = self.get_argument('pkg', '')
        product = self.get_argument('pid', '')
        ext_params = self.get_argument('ext', '{}')

        hold = self.settings['pay_conf'].process_prepay(sdk, uid, cid, price, pkg, product, ext_params, self.write_cb)
        if not hold:
            if not self.get_callback_url(sdk):
                self.finish()
                return
            oid = gen_order_id(cid)
            self.write('{{"order":"{}", "cb":"{}"}}'.format(oid, self.__rt_cache__[sdk]))
            self.finish()

    def write_cb(self, content):
        self.write(content)
        self.finish()

    def get_callback_url(self, sdk):
        if sdk not in self.__rt_cache__:
            cb_uri = None
            for item in self.settings['routine_info']:
                if item[1] == self.get_cls_by_sdk(sdk):
                    cb_uri = 'http://{}{}'.format(
                        self.settings['domain'], item[0])
            if not cb_uri:
                logging.fatal('can not get a callback.')
                self.set_status(500, 'server error.')
                return False
            self.__rt_cache__[sdk] = cb_uri
        return True

    @staticmethod
    def get_cls_by_sdk(sdk):
        if sdk == words.FafaPayTag:
            return FfCallbackHandler
        elif sdk == words.RongMengTag:
            return RongmengNotifyHandler
        return None


class CommonCallback(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def post(self, api_name):
        self.settings['pay_conf'].process_notify(self, api_name, self.on_process_finish)

    def on_process_finish(self, out):
        if out:
            self.write(out)
        self.finish()

    @tornado.web.asynchronous
    def get(self, api_name):
        self.settings['pay_conf'].process_notify(self, api_name, self.on_process_finish)


class SuccessHandler(tornado.web.RequestHandler):
    def get(self):
        self.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>PaySuccess</title>
</head>
<body>
支付成功!
</body>
</html>''')
