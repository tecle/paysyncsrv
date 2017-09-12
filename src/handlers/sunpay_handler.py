# -*- coding: utf-8 -*-

# 阳光支付

import json
import logging
import tornado.web
import tornado.gen
from words import SunPayTag
from model.order_model import ThirdPayOrders
from model.table_base import Wanted
from tornado.httpclient import AsyncHTTPClient
from util_tools import gen_order_id


class SunPrePayHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        uid = self.get_argument('uid')
        price = int(self.get_argument('price'))
        product = self.get_argument('pid')
        product_name = self.get_argument('pname')
        channel_id = self.get_argument('cid')
        ext_data = self.get_argument('ext', '')
        pkg = self.get_argument('pkg')
        pay_type = self.get_argument('pt', '')
        oid = gen_order_id()

        req = self.settings['pay_conf'].build_sun_prepay_request(
            oid, product, product_name, price, pay_type, self.get_callback_url(), ext_data)
        rsp = yield tornado.gen.Task(AsyncHTTPClient().fetch, req)
        if rsp.error:
            return
        obj = json.loads(rsp.body)
        if obj['Result'] != "SUCCESS":
            logging.warning('get sun prepay failed.[{}]'.format(rsp.body))
            return
        data = obj['Data']
        order = ThirdPayOrders()
        order.order_id = oid
        order.channel = channel_id
        order.uid = uid
        order.product = product
        order.pkg = pkg
        order.price = price
        order.tag = SunPayTag
        order.ext = '{{"data":"{}", "pay_type":"{}"}}'.format(data, pay_type)
        order.save()
        self.write('{{"data": "{}", "code": 200, "pay_type":"{}", "order": "{}"}}'.format(data, pay_type, oid))

    def get_callback_url(self, app_cache=[]):
        '''
        :param app_cache: use default, do not pass it to here!
        :return:
        '''
        if app_cache:
            return app_cache[0]
        for item in self.settings['routine_info']:
            if item[1] == SunPayCallbackHandler:
                cb_uri = 'http://{}{}'.format(
                    self.settings['domain'], item[0])
                app_cache.append(cb_uri)
                return cb_uri
        raise Exception('can not get a callback.')


class SunPayCallbackHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        pay_type = self.get_argument('payType')
        oid = self.get_argument('mchOrderNo')
        trans_id = self.get_argument('order_no')
        price = self.get_argument('price')
        end_time = self.get_argument('payEndTime')
        ext_data = self.get_argument('mark')
        res = self.get_argument('result')
        sign = self.get_argument('sign')
        if res != 'SUCCESS':
            self.write('SUCCESS')
            return
        if not self.settings['pay_conf'].check_sun_sign(
                pay_type, oid, trans_id, price, end_time, ext_data, res, sign):
            self.write('FAIL')
            return
        order = ThirdPayOrders()
        order.order_id = oid
        order.success = Wanted
        order.channel = Wanted
        res = yield tornado.gen.Task(order.update_from_db)
        if not res:
            logging.warning('order [{}] not exist.'.format(oid))
            self.write('FAIL')
            return
        if not order.success:
            no = ThirdPayOrders()
            no.order_id = oid
            no.success = True
            no.visible = self.settings['server_conf'].may_deduct(order.channel)
            no.update_to_db()
        self.write('SUCCESS')


class QueryToRemoteHandler(tornado.web.RequestHandler):

    '''当使用通用查询接口查不到订单消息时，使用此接口查询远端订单'''
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        order_id = self.get_argument('oid')
        req = self.settings['pay_conf'].build_sun_query_request(order_id)
        rsp = yield tornado.gen.Task(AsyncHTTPClient().fetch, req)
        if not rsp.error:
            try:
                obj = json.loads(rsp.body)
                logging.info('order [{}] status:[{}]'.format(order_id, obj['Data']))
                if obj['Data'].strip() == 'true':
                    order = ThirdPayOrders()
                    order.order_id = order_id
                    order.channel = Wanted
                    order.price = Wanted
                    res = yield tornado.gen.Task(order.update_from_db)
                    if res:
                        order.success = True
                        order.visible = self.settings['server_conf'].may_deduct(order.channel)
                        order.update_to_db()
                    out = '{{"code":200, "msg":"", "price":{}, "channel":"{}"}}'.format(order.price, order.channel)
                elif obj['Data'].strip() == 'false':
                    out = '{"code":203, "msg": "order not success.", "price":0, "channel": ""}'
                else:
                    out = '{"code":205, "msg": "order not exist.", "price":0, "channel": ""}'
            except Exception:
                logging.exception('parse response [{}] failed'.format(rsp.body))
                out = '{"code":204, "msg": "parse remote response failed.", "price":0, "channel": ""}'
        else:
            out = '{"code":206, "msg": "remote return bad status.", "price":0, "channel": ""}'
        self.write(out)
