# -*- coding: utf-8 -*-

import hashlib
import words
import logging
import datetime
from pay.ipay import SmsPayInterface
from functools import partial


class BeiAiPay(SmsPayInterface):
    def __init__(self, obj, *args):
        super(BeiAiPay, self).__init__(obj, *args)
        self.success_text = 'OK'
        self.key = obj.get('key', '')
        self.need_verify_sign = self.key and obj.get('verify_sign', False)

    def do_biz(self, handler, callback):
        extra = {}
        trans_id = handler.get_argument('OutTradeNo')
        order_time = handler.get_argument('OrderTime')
        order_id = handler.get_argument('OrderId')
        pay_st = handler.get_argument('Status')
        price = handler.get_argument('Fee')
        biz_param = handler.get_argument('CpParam')
        sign = handler.get_argument('Sign')
        if not self.verify_sign(sign, trans_id, order_time, order_id, pay_st, price, biz_param):
            callback('Invalid Sign.')
            return
        trans_id = self._normalize_trans_id(trans_id, extra)
        order_id = self._normalize_order_id(order_id, extra)
        pay_result = int(pay_st)
        order_time = datetime.datetime.strptime(order_time, '%Y%m%d%H%M%S').strftime("%Y-%m-%d %H:%M:%S")
        channel = handler.get_argument('ChannelId')
        pay_type = self.transform_op_type(int(handler.get_argument('CarrierType')))
        extra.update({
            'province': handler.get_argument('Province', ''),
            'app_id': handler.get_argument('AppId'),
            'sdk_ver': handler.get_argument('Version'),
            'order_part': handler.get_argument('SubIndex')
        })
        uid = hashlib.md5(handler.get_argument('OutTradeNo')).hexdigest()

        order = self.make_order(
            words.BeiAiPayTag, order_id, uid, channel, int(float(price) * 100),
            words.message_package, words.message_product,
            pay_type, ext_data=self._dump_extra(extra), trans_id=trans_id
        )
        order.success = pay_result
        order.create_time = order_time

        self.table_cls.get_one(
            order_id,
            callback=partial(self.on_finish_get_order, order, callback)
        )

    def verify_sign(self, sign, *args):
        if self.need_verify_sign:
            expect = hashlib.md5('#'.join(args + (self.key,))).hexdigest()
            if expect != sign:
                logging.warning('Invalid sign. expect:{}, actual:{}'.format(expect, sign))
                return False
        return True

    @staticmethod
    def transform_op_type(op_type):
        mapping = ('CMCC', 'CU', 'CT')  # 中国移动,中国联通,中国电信
        return mapping[op_type]
