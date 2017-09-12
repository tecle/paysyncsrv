# coding:utf-8

# -*- 微米支付 -*-

import json
import words
import urllib
import logging
import tornado.web
import tornado.gen
from model.order_model import ThirdPayOrders
from model.table_base import Wanted
from tornado.httpclient import AsyncHTTPClient


class WmPrepayHandler(tornado.web.RequestHandler):
    CP = 'ol100013'
    URL = "http://121.199.6.130:10086/apppay/apppay2"

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self, *args, **kwargs):
        price = int(self.get_argument('fee'))
        pkg = self.get_argument('pkg')
        md5 = self.get_argument('md5')
        imei = self.get_argument('imei')
        ext = self.get_argument('oid')
        uid = self.get_argument('uid')
        channel_id = self.get_argument('cid')
        product = self.get_argument('pid', 'Unknown')
        params = {
            'fee': price,
            'extData': ext,
            'partnerid': self.CP,
            'pkgName': pkg,
            'md5': md5,
            'imei': imei
        }
        resp = yield AsyncHTTPClient().fetch('{}?{}'.format(self.URL, urllib.urlencode(params)))
        if resp.error:
            logging.warning('query to remote server error:{}'.format(resp.body))
            self.set_status(601, 'remote server error:{}'.format(resp.body))
            return
        obj = json.loads(resp.body)
        if 'code' not in obj or obj['code'] != "200":
            logging.warning('query to remote server error:{}'.format(resp.body))
            self.set_status(601, 'remote server error:{}'.format(obj['msg']))
            return
        if self.CP != obj['partnerid']:
            self.set_status(602, 'partnerid error.')
            return
        appid = obj['data']['appid']
        token_id = obj['data']['token_id']
        order = ThirdPayOrders()
        order.pkg = pkg
        order.order_id = ext
        order.uid = uid
        order.trans_id = obj['orderid']
        order.tag = words.WiMiTag
        order.price = price
        order.product = product
        order.channel = channel_id
        order.ext = '{{"appid":"{}", "token":"{}", "pkg":"{}", "imei":"{}"}}'.format(appid, token_id, pkg, imei)
        order.save()
        self.write('{{"appid":"{}", "token":"{}"}}'.format(appid, token_id))


class WmCallbackHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def get(self, *args, **kwargs):
        trans_id = self.get_argument('orderid')
        fee = self.get_argument('fee')
        order_id = self.get_argument('extData')
        openid = self.get_argument('openid')
        appid = self.get_argument('appid')
        debug_str = '{}&{}&{}&{}&{}'.format(trans_id, fee, order_id, openid, appid)
        db_order = ThirdPayOrders()
        db_order.order_id = order_id
        db_order.channel = Wanted
        res = yield tornado.gen.Task(db_order.update_from_db)
        if not res:
            logging.warning('no order with info[{}] in db.'.format(debug_str))
            self.write('fail')
            return
        else:
            db_order.stat = words.WiMiSuccessStat
            db_order.visible = self.settings['server_conf'].may_deduct(db_order.channel)
            db_order.success = True
            db_order.update_to_db()
        self.write('ok')


class WmOrderStatusHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        oid = self.get_argument('oid')
        order = ThirdPayOrders()
        order.order_id = oid
        order.price = Wanted
        order.stat = Wanted
        order.success = Wanted
        order.tag = Wanted
        res = yield tornado.gen.Task(order.update_from_db)
        logging.info(order)
        if not res or order.tag != words.WiMiTag or not order.success:
            self.write('{"code":201, "price": 0}')
        else:
            self.write('{{"code":200, "price": {}}}'.format(order.price))


class WmQueryHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        uid = self.get_argument('uid')
        channel = self.get_argument('channel')
        success, db_orders = \
            yield tornado.gen.Task(ThirdPayOrders.get_some, 'uid="{}" and channel="{}"'.format(uid, channel))
        if not success:
            self.write('[]')
            return
        res = []
        for item in db_orders:
            if item.tag != words.WiMiTag:
                continue
            if item.stat != words.WiMiSuccessStat:
                continue

            res.append({'price': item.price, 'oid': item.order_id})
        self.write(json.dumps({"code": 200, "orders": res}))
