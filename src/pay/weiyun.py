# -*- coding: utf-8 -*-

import hashlib
import words
from util_tools import gen_order_id
from pay.ipay import SmsPayInterface
from functools import partial


class WeiYunPay(SmsPayInterface):
    def __init__(self, *args):
        super(WeiYunPay, self).__init__(*args)
        self.success_text = 'ok'

    def do_biz(self, handler, callback):
        app_code = handler.get_argument("app_code")
        channel = handler.get_argument('channel')
        mobile = handler.get_argument('mobile')
        uid = hashlib.md5(handler.get_argument('imei')).hexdigest()
        price = int(handler.get_argument('price'))
        trans_id = handler.get_argument('orderId')
        order_time = handler.get_argument('orderTime')
        pay_result = int(handler.get_argument('feeResult'))
        order_id = gen_order_id()
        extra = {'phone': mobile, 'app_id': app_code}
        trans_id = self._normalize_trans_id(trans_id, extra)
        order = self.make_order(
            words.WeiYunPayTag, order_id, uid, channel, price, words.message_package, words.message_product,
            words.message_pay_type, ext_data=self._dump_extra(extra), trans_id=trans_id)
        order.success = 1 if pay_result == 0 else 0
        order.create_time = order_time

        self.table_cls.raw_sql(
            "select order_id, success from {} where trans_id=%s order by create_time limit 0, 1".format(
                self.table_cls.get_table_name()),
            trans_id,
            callback=partial(self.on_finish_get_order, order, callback))
