# coding: utf-8


import json
import words
import hashlib
import logging
import tornado.web
import tornado.gen
from model.order_model import ThirdPayOrders
from model.table_base import Wanted


class FfCallbackHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    @tornado.gen.coroutine
    def post(self):
        try:
            obj = json.loads(self.request.body, encoding='utf-8')
            sign = self.get_sign(obj)
            if sign != obj['Sign'].lower():
                raise Exception('Invalid sign.')
            if obj['Error'] == 1:
                db_order = ThirdPayOrders()
                db_order.order_id = obj['OutTradeNo']
                db_order.success = Wanted
                res = yield tornado.gen.Task(db_order.update_from_db)
                if not res:
                    # channel_id,user_id,product_id
                    ext = obj['TradeAttach'].split(',')
                    order = ThirdPayOrders()
                    order.order_id = obj['MchTradeNo']
                    order.price = obj['ActuallyMoney']
                    order.channel = ext[0]
                    order.uid = ext[1]
                    order.product = ext[2]
                    order.pkg = ext[3]
                    order.tag = words.FafaPayTag
                    order.success = True
                    order.trans_id = obj['OutTradeNo']
                    order.ext = '{{"MchId":{}, "Time":{}}}'.format(obj['MchId'], obj['TimeEnd'])
                    order.visible = self.settings['server_conf'].may_deduct(order.channel)
                    order.save()
                elif not db_order.success:
                    db_order.success = True
                    db_order.update_to_db()
            else:
                raise Exception('call back failed.')
        except Exception:
            logging.exception('bad callback for fafa:[{}]'.format(self.request.body))
            self.write('fail')
            return
        self.write('success')

    def get_sign(self, obj):
        return self.settings['pay_conf'].fafa.get_sign(
            str(obj['Error']),
            obj['Message'],
            obj['MchId'],
            obj['MchTradeNo'],
            obj['OutTradeNo'],
            obj['TradeAttach'],
            str(obj['ActuallyMoney']),
            str(obj['TimeEnd']),
        )
