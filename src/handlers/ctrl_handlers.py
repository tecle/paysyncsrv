# coding: utf-8

import time
import hashlib
import logging
import tornado.web


class CtrlHandler(tornado.web.RequestHandler):
    __sign_key__ = 'FxxopOSksdIX72_I1'

    def post(self):
        op = self.get_argument('op', None)
        ts = self.get_argument('ts', None)
        sign = self.get_argument('sign', None)
        if not op or not ts or not sign:
            self.set_status(502, 'param err.')
            return
        if time.time() - int(ts) > 10:
            self.set_status(500, 'sign err.')
            return
        pub_str = '{}&{}'.format(op, ts)
        res = False
        if op == 'DEDUCT':
            res = self.update_deduct(pub_str, sign)
        elif op == 'SPT':
            res = self.switch_pay_type(pub_str, sign)
        else:
            logging.warning('invalid op [{}] from [{}]'.format(op, self.request.remote_ip))
        self.write('OK' if res else 'FAIL')

    def switch_pay_type(self, pub, sign):
        tag = self.get_argument('tag')
        pt = self.get_argument('pt')
        if self.get_sign(pub, tag, pt) != sign:
            self.set_status(501, 'sign incorrect.')
            return False
        self.settings['server_conf'].switch_pay_type(tag, pt)
        logging.info('IP [{}] switch pay type [{}]->[{}]'.format(self.request.remote_ip, tag, pt))
        return True

    def update_deduct(self, pub, sign):
        channel_id = self.get_argument('cid')
        dr = self.get_argument('dr')
        if self.get_sign(pub, channel_id, dr) != sign:
            self.set_status(501, 'sign incorrect.')
            return False
        logging.info('IP [{}] update deduct rate [{}]->[{}]'.format(self.request.remote_ip, channel_id, dr))
        return self.settings['server_conf'].modify_deduct(channel_id, dr)

    def get_sign(self, *args):
        str_to_sign = '{}&{}'.format('&'.join(args), self.__sign_key__)
        logging.info('str to sign[{}]'.format(str_to_sign))
        return hashlib.md5(str_to_sign).hexdigest()
