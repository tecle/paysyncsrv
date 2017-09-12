# -*- coding: utf-8 -*-

import random
import urllib
import base64
import logging
import words
from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES
from Crypto.Hash import SHA
from util_tools import gen_order_id
from model.order_model import ThirdPayOrders
from model.table_base import Wanted
from functools import partial
from pay.ipay import PayInterface


class FanWeiPay(PayInterface):
    def __init__(self, obj, notify_url, srv_conf):
        # self.encryptor = RSA.importKey(obj['private_key'])
        # self.decryptor = RSA.importKey(obj['public_key'])
        self.encryptor = RSA.importKey(obj['public_key'])
        self.decryptor = RSA.importKey(obj['private_key'])
        self.signer = PKCS1_v1_5.new(self.decryptor)
        self.mch_no = obj['mch_no']
        self.key = obj['key']
        self.prepay_url = obj['prepay_url']
        self.df_pay_type = obj.get('default_pay_type', None)
        super(FanWeiPay, self).__init__(notify_url, srv_conf)
        self.notify_url = '{}/{}'.format(self.notify_url, words.FanWeiPayTag)
        self.success_text = 'success'
        self.parse_pay_type_conf(obj)
        self.pay_type_converter = {}
        for k, v in self.pay_type_adapter.items():
            self.pay_type_converter[v] = k
        self.aes_mode = AES.MODE_CBC

    def rsa_encode(self, data):
        return base64.b64encode(self.encryptor.encrypt(data, 0)[0])

    def rsa_decode(self, data):
        return self.decryptor.decrypt(base64.b64decode(data))

    def rsa_sign(self, data):
        logging.debug('digest:[{}]'.format(data + self.key))
        return base64.b64encode(self.signer.sign(SHA.new(data + self.key)))

    def verify_sign(self, sign2str, sign):
        return self.encryptor.verify(SHA.new(sign2str + self.key), base64.b64decode(sign))

    @staticmethod
    def random_string():
        candidate = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        key = ''
        for i in xrange(16):
            key += random.choice(candidate)
        return key

    def process_prepay(self, uid, cid, price, pkg, pid, ext_params, callback=None):
        order_id = gen_order_id()
        cn_pay_type = ext_params
        self.save_order(uid, order_id, cid, pkg, price, words.FanWeiPayTag, pid)
        callback(self.make_prepay_data(order_id, cn_pay_type, self.notify_url))
        return True

    def process_notify(self, handler, callback):
        msg = handler.get_argument('message')
        sign = handler.get_argument('signature')
        params, str2sign = self.decode_response(msg)
        if self.verify_sign(str2sign, sign):
            order_id = params['payid']
            trans_id = params['orderNo']
            pay_status = int(params['state'])
            pay_time = params['modifyTime']
            pay_method = params['payMethod']
            pay_type = params['payMethodType']
            if pay_status == 2:
                order = ThirdPayOrders()
                order.order_id = order_id
                order.success = Wanted
                order.channel = Wanted
                order.update_from_db(callback=partial(
                    self.on_update_over, order,
                    (trans_id, self.pay_type_converter.get(pay_type, None),
                     '{{"time":"{}", "pay_method":"{}"}}'.format(pay_time, pay_method)), callback))
            else:
                callback(self.success_text)
        else:
            callback('fail...')

    def encode_request(self, params):
        raw_message = urllib.urlencode(params)
        ext_chr_len = len(raw_message) % 16
        if ext_chr_len != 0:
            for i in range(16 - ext_chr_len):
                raw_message += '\0'
        key = self.random_string()
        iv = self.random_string()
        logging.debug('key:[{}]'.format(key))
        logging.debug('iv:[{}]'.format(iv))
        logging.debug('string:[{}]'.format(raw_message))
        aes_encryptor = AES.new(key, mode=self.aes_mode, IV=iv)
        message = self.rsa_encode(key) + self.rsa_encode(iv) + base64.b64encode(aes_encryptor.encrypt(raw_message))
        digest = ''.join(params.values())
        sign = self.rsa_sign(digest)
        logging.debug('message:[{}]'.format(message))
        logging.debug('signature:[{}]'.format(sign))
        return message, sign

    def decode_response(self, data):
        key = self.rsa_decode(data[:172])
        iv = self.rsa_decode(data[172:172 + 172])
        msg = base64.b64decode(data[172 + 172:])
        aes_decryptor = AES.new(key, self.aes_mode, iv)
        raw_msg = aes_decryptor.decrypt(msg).strip()
        logging.debug(raw_msg)
        params = {}
        digest = []
        for s in raw_msg.split('&'):
            pair = s.split('=')
            value = urllib.unquote(pair[1])
            digest.append(value)
            params[pair[0]] = value
        return params, ''.join(digest)
