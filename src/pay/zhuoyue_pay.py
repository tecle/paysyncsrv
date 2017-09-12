# -*- coding: utf-8 -*-

import logging
import words
from util_tools import gen_order_id
from model.order_model import ThirdPayOrders
from model.table_base import Wanted
from functools import partial
from pay.ipay import PayInterface


class ZhuoYuePay(PayInterface):
    def __init__(self, obj, notify_url, srv_conf):
        super(ZhuoYuePay, self).__init__(notify_url, srv_conf)
        self.df_pay_type = obj.get('default_pay_type', None)
        self.mch_no = obj['mch_no']
        self.notify_url = '{}/{}'.format(self.notify_url, words.ZhuoYuePayTag)
        self.success_text = 'success'
        self.parse_pay_type_conf(obj)
        self.pay_type_converter = {}  # special -> system
        for k, v in self.pay_type_adapter.items():
            self.pay_type_converter[v] = k
        self.fix_len = len(self.mch_no) + 1
        self.dyn_len = 20 - self.fix_len

    def process_prepay(self, uid, cid, price, pkg, pid, ext_params, callback=None):
        order_id = gen_order_id()
        if len(order_id) > self.dyn_len:
            order_id = '{}_{}'.format(self.mch_no, order_id[:self.dyn_len - len(order_id)])
        else:
            order_id = '{}_{}'.format(self.mch_no, order_id)
        if not self.server_conf.validate_pay_method(ext_params):
            cn_pay_type = ext_params
            pay_type = self.pay_type_converter.get(cn_pay_type, None)
            self.save_order(uid, order_id, cid, pkg, price, words.ZhuoYuePayTag, pid, pay_type=pay_type)
            callback(self.make_prepay_data(order_id, cn_pay_type, self.notify_url))
        else:
            pay_type = self.server_conf.get_pay_type_by_tag(words.ZhuoYuePayTag, ext_params)
            if not pay_type:
                logging.warning('cannot find pay setting for zy with pay method:' + ext_params)
                callback(self.make_prepay_data('', '', ''))
            else:
                cn_pay_type = self.pay_type_adapter.get(pay_type, None)
                self.save_order(uid, order_id, cid, pkg, price, words.ZhuoYuePayTag, pid, pay_type=pay_type)
                callback(self.make_prepay_data(order_id, cn_pay_type, self.notify_url))
        return True

    def process_notify(self, handler, callback):
        order_id = handler.get_argument('out_trade_no')
        pay_status = int(handler.get_argument('result'))
        pay_type = int(handler.get_argument('pay_type'))
        trans_id = handler.get_argument('out_transaction_id')
        ts = handler.get_argument('timestamp')
        if pay_status == 0:
            order = ThirdPayOrders()
            order.order_id = order_id
            order.success = Wanted
            order.channel = Wanted
            order.update_from_db(callback=partial(
                self.on_update_over, order,
                (trans_id, self.pay_type_converter.get(pay_type),
                 '{{"time":"{}", "pay_type": "{}"}}'.format(ts, pay_type)), callback))
            logging.info('order[{}] pay_type:[{}]'.format(order_id, pay_type))
        else:
            logging.info('order [{}] has a bad pay status.'.format(pay_status))
            callback(self.success_text)
