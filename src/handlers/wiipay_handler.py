# coding: utf-8
import logging
import os
import hashlib
import base64
import json

import tornado.web
import tornado.gen

from model.order_model import CommonOrders
import words

CUR_PATH = os.path.split(os.path.realpath(__file__))[0]


class WiiQueryHandlerV2(tornado.web.RequestHandler):
    member_year = "365"
    member_forever = "36500"
    year_num = 2900
    forever_num = 5900

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        uid = self.get_argument("uid")
        success, ans = yield tornado.gen.Task(CommonOrders.get_some, 'uid=%s and tag="WP"', None, uid)
        if not success:
            logging.warning('query db failed.')
            return
        role = ''
        for order_info in ans:
            if order_info.price == self.forever_num:
                role = self.member_forever
                break
            elif order_info.price == self.year_num:
                role = self.member_year
        self.write(role)


class WiiHandlerV2(tornado.web.RequestHandler):
    app_key = 'RKMMPsII'

    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self, *args, **kwargs):
        cpparam = self.get_argument('cpparam')
        order_no = self.get_argument('orderNo')
        status = self.get_argument('status')
        price = self.get_argument('price')
        ts = self.get_argument('time')
        syn_type = self.get_argument('synType')
        s = 'cpparam={}&orderNo={}&price={}&status={}&synType={}&time={}{}'.format(
            cpparam, order_no, price, status, syn_type, ts, self.app_key)
        sign = hashlib.md5(s).hexdigest()
        if sign.upper() != self.get_argument('sign').upper():
            logging.warning('invalid sign:{}, expect:{}'.format(s, sign))
            self.write('failed, invalid sign.')
            return

        tmp = json.loads(base64.b64decode(cpparam)).get('param', '').split(',')
        if len(tmp) != 2:
            logging.warning('invalid cpparam:[{}]'.format(base64.b64decode(cpparam)))
            self.write('failed, invalid cpparam.')
            return

        order = CommonOrders()
        order.trans_id = order_no
        order.order_id = tmp[0]
        order.uid = tmp[1]
        order.stat = status
        order.price = int(float(price) * 100)
        order.tag = words.WiPayTag
        order.other = '{{"time":{}, "synType":{}}}'.format(ts, syn_type)
        db_order = yield tornado.gen.Task(CommonOrders.get_one, order.order_id)
        if db_order:
            if db_order != 'success':
                new_order = CommonOrders()
                new_order.order_id = order.order_id
                new_order.stat = order.stat
                new_order.update_to_db()
        else:
            logging.info('save new pay[{}]'.format(s))
            order.save()
        self.write('success')
