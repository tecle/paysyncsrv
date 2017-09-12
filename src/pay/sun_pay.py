# -*- coding: utf-8 -*-

import json
import urllib
import base64
import logging
import words
from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Hash import MD5
from util_tools import gen_order_id
from model.order_model import ThirdPayOrders
from model.table_base import Wanted
from functools import partial
from pay.ipay import PayInterface


class SunPay(PayInterface):
    def __init__(self, obj, notify_url, srv_conf):
        self.signer = PKCS1_v1_5.new(RSA.importKey(obj['private_key']))
        self.verifier = PKCS1_v1_5.new(RSA.importKey(obj['public_key']))
        self.mch_no = obj['mch_no']
        self.prepay_url = obj['prepay_url']
        self.query_url = obj['query_url']
        self.df_pay_type = obj.get('default_pay_type', None)
        super(SunPay, self).__init__(notify_url, srv_conf)
        self.notify_url = '{}/{}'.format(self.notify_url, words.SunPayTag)
        self.success_text = 'SUCCESS'
        self.parse_pay_type_conf(obj)

    def process_prepay(self, uid, cid, price, pkg, pid, ext_params, callback=None):
        obj = json.loads(ext_params)
        product_name = obj['pname']
        if 'pm' in obj:
            pay_type = self.server_conf.get_pay_type_by_tag(words.SunPayTag, obj['pm'])
        else:
            pay_type = 'A.wap'
        logging.debug('pay_type:[{}]'.format(pay_type))
        cn_pay_type = self.pay_type_adapter.get(pay_type, self.df_pay_type)
        order_id = gen_order_id()
        keys = ('mchNo', 'mchOrderNo', 'productId', 'productName', 'price', 'payType',
                'returnUrl', 'notifyUrl', 'mark', 'sign')
        vals = [
            self.mch_no, order_id, pid, product_name, '{:.2f}'.format(price / 100.0),
            cn_pay_type, self.web_success_page, self.notify_url, ''
        ]
        str_to_sign = '|'.join(vals)
        sign = base64.b64encode(self.signer.sign(MD5.new(str_to_sign.encode('utf-8'))))
        vals.append(sign)
        query = {}
        for i, key in enumerate(keys):
            query[key] = vals[i].encode('utf-8')
        logging.info('curl -X POST "{}" -d \'{}\''.format(self.prepay_url, urllib.urlencode(query)))
        self.save_order(
            uid, order_id, cid, pkg, price, words.SunPayTag, product=pid, pay_type=pay_type)
        out = self.make_prepay_data(order_id, cn_pay_type, '{}?{}'.format(self.prepay_url, urllib.urlencode(query)))
        if callback:
            callback(out)
        else:
            return out

    def process_notify(self, handler, callback):
        pay_type = handler.get_argument('payType')
        oid = handler.get_argument('mchOrderNo')
        trans_id = handler.get_argument('order_no')
        price = handler.get_argument('price')
        end_time = handler.get_argument('payEndTime')
        ext_data = handler.get_argument('mark')
        res = handler.get_argument('result')
        sign = handler.get_argument('sign')
        if res != 'SUCCESS':
            callback('SUCCESS')
            return
        if not self.check_sign(
                pay_type, oid, trans_id, price, end_time, ext_data, res, sign):
            callback('FAIL')
            return
        logging.info('order[{}] pay_type:[{}]'.format(oid, pay_type))
        order = ThirdPayOrders()
        order.order_id = oid
        order.success = Wanted
        order.channel = Wanted
        order.update_from_db(callback=partial(self.on_update_over, order, (None, None, None), callback))

    def check_sign(self, pay_type, order_id, trans_id, price, end_time, mark, result, src_sign):
        str_2_sign = '|'.join((pay_type, order_id, trans_id, price, end_time, mark, result))
        return self.verifier.verify(MD5.new(str_2_sign), base64.b64decode(src_sign))
