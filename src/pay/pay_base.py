# -*- coding: utf-8 -*-

import json
import urllib
import base64
import logging
import hashlib
import words
from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Hash import MD5
from tornado.httpclient import HTTPRequest
from util_tools import gen_order_id
from model.order_model import ThirdPayOrders
from model.table_base import Wanted
from functools import partial
from pay.ipay import PayInterface
from pay.sun_pay import SunPay
from pay.fanwei_pay import FanWeiPay
from pay.zhuoyue_pay import ZhuoYuePay
from pay.yuechang_pay import YueChangPay
from pay.weiyun import WeiYunPay
from pay.zhongzhi import ZhongZhiPay
from pay.beiai import BeiAiPay
from pay.maiguang import MaiGuangPay
from pay.duoyile import DuoYiLePay


class FaFaPay(object):
    def __init__(self, obj):
        self.mch_no = obj['FF']['mch_no']
        self.key = obj['FF']['key']

    def get_sign(self, err, msg, mch_id, order_no, trans_no, attach, price, ts):
        return hashlib.md5(
            ''.join((err, msg or '', mch_id, order_no, trans_no, attach or '', price, ts, self.key)).encode(
                'utf-8')).hexdigest()


class WQBPay(PayInterface):
    def __init__(self, obj, notify_url, dd_conf):
        self.mch_no = obj['mch_no']
        self.key = obj['key']
        self.prepay_url = obj['prepay_url']
        super(WQBPay, self).__init__(notify_url, dd_conf)
        self.notify_url = '{}/{}'.format(self.notify_url, words.WeiQianBao)
        self.success_text = 'ok'

    def process_prepay(self, uid, cid, price, pkg, pid, ext_params, callback=None):
        oid = gen_order_id(words.WeiQianBao)
        self.save_order(uid, oid, cid, pkg, price, words.WeiQianBao, product=pid)
        out = self.make_prepay_data(oid, '', self.build_prepay_request(price, oid, ext_params))
        if callback:
            callback(out)
        else:
            return out

    def build_prepay_request(self, price, order_no, pay_type):
        price = '{:.2f}'.format(price / 100.0)
        sign = hashlib.md5('{}|{}|{}'.format(self.mch_no, price, self.key)).hexdigest()
        return '{}?{}'.format(self.prepay_url, urllib.urlencode({
            'mchno': self.mch_no,
            'money': price,
            'orderno': order_no,
            'payType': pay_type,
            'notifyUrl': self.notify_url,
            'sign': sign
        }))

    def process_notify(self, handler, callback):
        result = handler.get_argument('result')
        price = handler.get_argument('money')
        pay_mch_no = handler.get_argument('paymentno')
        order_no = handler.get_argument('orderno')
        paytime = handler.get_argument('paytime')
        pay_type = handler.get_argument('payType')
        sign = handler.get_argument('sign2')
        if result != '1':
            callback(self.success_text)
        elif sign != self.get_sign(price, pay_mch_no):
            logging.info('invalid sign, expect:[{}], actual[{}]'.format(self.get_sign(price, pay_mch_no), sign))
            callback('fail')
        else:
            order = ThirdPayOrders()
            order.order_id = order_no
            order.success = Wanted
            order.channel = Wanted
            order.update_from_db(callback=partial(
                self.on_update_over, order, (None, None, '{{"time":"{}"}}'.format(paytime)), callback))

    def get_sign(self, money, pay_mch_no):
        return hashlib.md5('|'.join((money, self.mch_no, pay_mch_no, self.key)).encode('utf-8')).hexdigest()


class PayFactory(object):
    def __init__(self, conf_file, domain, dd_conf):
        with open(conf_file) as f:
            obj = json.load(f)
        self._init_sun_pay_(obj)
        self.fafa = FaFaPay(obj)
        self.inst_map = {
            words.WeiQianBao: WQBPay(obj[words.WeiQianBao], domain, dd_conf),
            words.SunPayTag: SunPay(obj[words.SunPayTag], domain, dd_conf),
            words.FanWeiPayTag: FanWeiPay(obj[words.FanWeiPayTag], domain, dd_conf),
            words.ZhuoYuePayTag: ZhuoYuePay(obj[words.ZhuoYuePayTag], domain, dd_conf),
            words.YueChangPayTag: YueChangPay(obj[words.YueChangPayTag], domain, dd_conf),
            words.WeiYunPayTag: WeiYunPay(obj[words.WeiYunPayTag], domain, dd_conf),
            words.ZhongZhiPayTag: ZhongZhiPay(obj[words.ZhongZhiPayTag], domain, dd_conf),
            words.BeiAiPayTag: BeiAiPay(obj[words.BeiAiPayTag], domain, dd_conf),
            words.MaiGuangTag: MaiGuangPay(obj[words.MaiGuangTag], domain, dd_conf),
            words.DuoYiLeTag: DuoYiLePay(obj[words.DuoYiLeTag], domain, dd_conf)
        }

    def process_prepay(self, sdk, uid, cid, price, pkg, pid, ext_params, callback):
        if sdk not in self.inst_map:
            return False
        self.inst_map[sdk].process_prepay(uid, cid, price, pkg, pid, ext_params, callback)
        return True

    def process_notify(self, handler, sdk, callback):
        if sdk in self.inst_map:
            self.inst_map[sdk].process_notify(handler, callback)
        else:
            logging.warning('API [{}] not exist.'.format(sdk))
            callback('fail')

    def _init_sun_pay_(self, obj):
        self.sun_signer = PKCS1_v1_5.new(RSA.importKey(obj['SUN']['private_key']))
        self.sun_verifier = PKCS1_v1_5.new(RSA.importKey(obj['SUN']['public_key']))
        self.sun_mch_no = obj['SUN']['mch_no']
        self.sun_df_pay = obj['SUN']['default_pay_type']
        self.sun_prepay = obj['SUN']['prepay_url']
        self.sun_query = obj['SUN']['query_url']

    def build_sun_prepay_request(self, order_id, product, product_name, price, pay_type, notify_url, ext_data=''):
        keys = (
            'mchNo', 'mchOrderNo', 'productId', 'productName', 'price', 'payType',
            'returnUrl', 'notifyUrl', 'mark', 'sign')
        vals = [
            self.sun_mch_no, order_id, product, product_name, '{:.2f}'.format(price / 100.0),
            pay_type or self.sun_df_pay, "", notify_url, ext_data
        ]
        str_to_sign = '|'.join(vals)
        sign = base64.b64encode(self.sun_signer.sign(MD5.new(str_to_sign.encode('utf-8'))))
        vals.append(sign)
        query = {}
        for i, key in enumerate(keys):
            query[key] = vals[i].encode('utf-8')
        logging.info('curl -X POST "{}" -d \'{}\''.format(self.sun_prepay, urllib.urlencode(query)))
        return HTTPRequest(self.sun_prepay, method='POST', body=urllib.urlencode(query))

    def check_sun_sign(self, pay_type, order_id, trans_id, price, end_time, mark, result, src_sign):
        str_2_sign = '|'.join((pay_type, order_id, trans_id, price, end_time, mark, result))
        return self.sun_verifier.verify(MD5.new(str_2_sign), base64.b64decode(src_sign))

    def build_sun_query_request(self, order_id):
        s = '{}|{}'.format(self.sun_mch_no, order_id)
        sign = base64.b64encode(self.sun_signer.sign(MD5.new(s)))
        param_str = urllib.urlencode({
            'mchNo': self.sun_mch_no,
            'mchOrderNo': order_id,
            'sign': sign
        })
        logging.info('query to SunServer:[curl -X POST "{}" -d \'{}\']'.format(self.sun_query, param_str))
        return HTTPRequest(self.sun_query, method='POST', body=param_str)
