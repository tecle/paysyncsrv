# -*- coding: utf-8 -*-

import datetime
import words
from util_tools import gen_order_id
from pay.ipay import SmsPayInterface
from functools import partial


class DuoYiLePay(SmsPayInterface):
    '''
    多益乐支付
    '''

    def __init__(self, *args):
        super(DuoYiLePay, self).__init__(*args)
        self.success_text = 'ok'

    def do_biz(self, handler, callback):
        extra = {'app_id': handler.get_argument("appId")}
        product = self._normalize_pid(handler.get_argument('chargePoint'), extra)
        trans_id = handler.get_argument('orderId')
        price = int(handler.get_argument('price'))
        extra['province_id'] = handler.get_argument('province', 'unknown')
        channel = handler.get_argument('channelId')
        pay_type = self.transform_op_type(handler.get_argument('operator'))
        uid = self._normalize_uid(handler.get_argument('imsi'), extra)
        extra['biz_param'] = handler.get_argument('cpparam')

        order_id = gen_order_id()
        order = self.make_order(
            words.DuoYiLeTag, order_id, uid, channel, price, words.message_package, product,
            pay_type, ext_data=self._dump_extra(extra), trans_id=trans_id)
        order.success = 1

        self.table_cls.raw_sql(
            "select order_id, success from {} where trans_id=%s order by create_time limit 0, 1".format(
                self.table_cls.get_table_name()),
            trans_id,
            callback=partial(self.on_finish_get_order, order, callback))

    @staticmethod
    def transform_op_type(origin):
        if origin == 'YD':
            return 'CMCC'
        if origin == 'LT':
            return 'CU'
        if origin == 'DX':
            return 'CT'
        return 'UNKNOWN'
