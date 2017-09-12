# -*- coding: utf-8 -*-

import json
import urllib
import logging
import hashlib
import words
from util_tools import gen_order_id
from model.order_model import ThirdPayOrders
from model.table_base import Wanted
from functools import partial
from pay.ipay import PayInterface
from tornado.httpclient import AsyncHTTPClient


class YueChangPay(PayInterface):
    def __init__(self, obj, notify_url, srv_conf):
        self.mch_no = obj['mch_no']
        self.key = obj['key']
        self.prepay_url = obj['prepay_url']
        self.df_pay_type = obj.get('default_pay_type', None)
        super(YueChangPay, self).__init__(notify_url, srv_conf)
        self.notify_url = '{}/{}'.format(self.notify_url, words.YueChangPayTag)
        self.success_text = 'success'
        self.parse_pay_type_conf(obj)

    def process_prepay(self, uid, cid, price, pkg, pid, ext_params, callback=None):
        obj = json.loads(ext_params)
        product_name = obj['pname']
        pay_type = self.server_conf.get_pay_type_by_tag(words.YueChangPayTag, obj['pm'])
        cn_pay_type = self.pay_type_adapter.get(pay_type, self.df_pay_type)
        order_id = "{}_{}".format(self.mch_no, gen_order_id())
        if cn_pay_type == 'weixin.apppay':
            self.save_order(
                uid, order_id, cid, pkg, price, words.SunPayTag, product=pid, pay_type=pay_type)
            callback(self.make_prepay_data(order_id, cn_pay_type, {
                "cb": self.notify_url,
                "ok": self.pay_success_page
            }))
        else:
            keys = ('aid', 'cent', 'itemname', 'oid', 'orderdesc', 'scburl')
            vals = [
                self.mch_no, str(price), product_name, order_id, product_name, self.notify_url, self.key
            ]
            str_to_sign = '|'.join(vals)
            logging.info(str_to_sign)
            sign = hashlib.md5(str_to_sign.encode('utf-8')).hexdigest()
            query = {key: vals[i] for i, key in enumerate(keys)}
            query['sign'] = sign
            query['ccburl'] = self.pay_success_page
            query['payway'] = cn_pay_type
            query['os'] = 'android'
            url = "{}?{}".format(self.prepay_url, urllib.urlencode(query))
            logging.info('curl "{}" '.format(url))
            params = (uid, order_id, cid, pkg, price, pid, pay_type, query, cn_pay_type, callback)
            AsyncHTTPClient().fetch(url, callback=partial(self.on_server_resp, params))

    def on_server_resp(self, params, resp):
        uid, order_id, cid, pkg, price, pid, pay_type, query, cn_pay_type, callback = params
        out = ''
        if not resp.error:
            obj = json.loads(resp.body)
            if obj['code'] == 0:
                self.save_order(
                    uid, order_id, cid, pkg, price, words.SunPayTag, product=pid, pay_type=pay_type)
                out = self.make_prepay_data(order_id, cn_pay_type, obj.get('payinfo', ''))
            else:
                logging.warning('request for prepay from server failed:[{}]'.format(resp.body))
        if callback:
            callback(out)

    def process_notify(self, handler, callback):
        aid = handler.get_argument('aid')
        billid = handler.get_argument('billid')
        cent = handler.get_argument('cent')
        itemname = handler.get_argument('itemname')
        oid = handler.get_argument('oid')
        ord_desc = handler.get_argument('orderdesc')
        str_to_sign = '|'.join((aid, billid, cent, itemname, oid, ord_desc, self.key))
        sign = hashlib.md5(str_to_sign).hexdigest()

        if sign == handler.get_argument('sign'):
            order = ThirdPayOrders()
            order.order_id = oid
            order.success = Wanted
            order.channel = Wanted
            order.update_from_db(callback=partial(self.on_update_over, order, (billid, None, None), callback))
        else:
            logging.warning('invalid sign.')
            callback('fail')
