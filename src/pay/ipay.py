# -*- coding: utf-8 -*-

import json
import hashlib
import logging
import types
from model.order_model import ThirdPayOrders, SmsPayOrders


class PayInterface(object):
    def __init__(self, domain, server_conf):
        self.pay_success_page = 'http://{}/mimi2/ok'.format(domain)
        self.notify_url = 'http://{}/mimi2/cb'.format(domain)
        self.server_conf = server_conf
        self.success_text = None
        self.web_success_page = 'http://{}/mimi2/ok'.format(domain)
        self.pay_type_adapter = {}  # 标准 -> 非标准
        self.table_cls = ThirdPayOrders

    def parse_pay_type_conf(self, obj):
        self.pay_type_adapter = obj.get('pay_type', {})

    def make_order(
            self, tag, order_id, uid, cid, price, pkg, pid, pay_type=None, ext_data=None, trans_id=None):
        order = self.table_cls()
        order.order_id = order_id
        order.uid = uid
        order.channel = cid
        order.tag = tag
        order.price = price
        order.pkg = pkg
        order.product = pid
        order.trans_id = trans_id
        order.ext = ext_data
        order.pay_type = pay_type
        return order

    def save_order(self, user_id, order_id, channel_id, pkg, price, tag,
                   product="UNKNOWN", ext_data=None, pay_type=None):
        order = self.make_order(tag, order_id, user_id, channel_id, price, pkg, product, pay_type, ext_data)
        order.save()

    def on_update_over(self, order, param_to_update, cb, success):
        '''
        :param order: ThirdPayOrders instance.
        :param param_to_update: [trans_id, pay_type, extra_data], value won't update if it is None.
        :param cb: callback function.
        :param success: update result.
        :return:
        '''
        if success and not order.success:
            no = ThirdPayOrders()
            no.order_id = order.order_id
            no.success = True
            no.visible = self.server_conf.may_deduct(order.channel)
            if param_to_update[2]:
                no.ext = param_to_update[2]
            if param_to_update[0]:
                no.trans_id = param_to_update[0]
            if param_to_update[1]:
                no.pay_type = param_to_update[1]
            no.update_to_db()
        elif not success:
            logging.warning('order [{}] not exist.'.format(order.order_id))
        cb(self.success_text)

    @staticmethod
    def make_prepay_data(order_id, pay_type, data):
        return json.dumps({
            "order": order_id,
            "pt": pay_type,
            "data": data
        }, ensure_ascii=False).encode('utf8')

    def process_prepay(self, uid, cid, price, pkg, pid, ext_params, callback=None):
        '''
        :param price: 单位分
        '''
        raise NotImplementedError('')

    def process_notify(self, handler, callback):
        raise NotImplementedError('')


class SmsPayInterface(PayInterface):
    def __init__(self, obj, *args):
        super(SmsPayInterface, self).__init__(*args)
        self.table_cls = SmsPayOrders
        remote_ip_conf = obj.get('remote_ip', [])
        self.host_list = None
        if isinstance(remote_ip_conf, types.StringTypes):
            if remote_ip_conf:
                self.host_list = {remote_ip_conf}
        elif isinstance(remote_ip_conf, list):
            self.host_list = set(remote_ip_conf)
        else:
            raise Exception('Invalid remote_ip type:{}'.format(type(remote_ip_conf)))

    def _normalize_uid(self, uid, extra):
        return self._normalize(uid, self.table_cls.uid_len(), 'uid', extra)

    def _normalize_order_id(self, oid, extra):
        return self._normalize(oid, self.table_cls.order_id_len(), 'order_id', extra)

    def _normalize_pid(self, pid, extra):
        return self._normalize(pid, self.table_cls.product_len(), 'product', extra)

    def _normalize_trans_id(self, tid, extra):
        return self._normalize(tid, self.table_cls.trans_id_len(), 'trade_id', extra)

    def on_finish_get_order(self, order, callback, orders):
        if not orders:
            order.visible = self.server_conf.may_deduct(order.channel) if order.success else 0
            order.save()
        else:
            db_order = orders[0] if isinstance(orders, list) else orders
            if not db_order.success and order.success:
                db_order.success = 1
                db_order.visible = self.server_conf.may_deduct(order.channel)
                db_order.update_to_db()
            else:
                logging.info('Order already record. Do nothing.')
        callback(self.success_text)

    @staticmethod
    def _normalize(origin, max_len, origin_name, extra):
        if isinstance(origin, str):
            logging.debug('expect unicode value for origin:{}, decode to unicode.'.format(origin))
            origin = origin.decode('utf-8')
        if len(origin) > max_len:
            ori = origin.encode('utf-8')
            n = hashlib.md5(ori).hexdigest()[:max_len]
            logging.info("{}:{} too long. normalize to:{}.".format(origin_name, ori, n))
            extra[origin_name] = origin
            return n
        return origin

    @staticmethod
    def _dump_extra(extra):
        return json.dumps(extra, ensure_ascii=False).encode('utf-8')

    def verify_ip(self, ip):
        if self.host_list:
            return ip in self.host_list or ip == '127.0.0.1'
        return True

    def process_notify(self, handler, callback):
        rip = handler.request.remote_ip
        if not self.verify_ip(rip):
            logging.warning('receive request from invalid ip:{}'.format(rip))
            if callback:
                callback('Invalid Ip')
        else:
            self.do_biz(handler, callback)

    def do_biz(self, handler, callback):
        raise NotImplementedError('do_biz not implement.')
