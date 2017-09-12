# -*- coding: utf-8 -*-

import words
import logging
import datetime
from util_tools import gen_order_id
from pay.ipay import SmsPayInterface
from functools import partial


class ZhongZhiPay(SmsPayInterface):
    def __init__(self, *args):
        super(ZhongZhiPay, self).__init__(*args)
        self.success_text = 'ok'

    def do_biz(self, handler, callback):
        extra = {'app_id': handler.get_argument("app_id")}
        channel = handler.get_argument('channel_id', "")
        if not channel:
            channel = handler.get_argument('callback_args')
        pay_type = self.transform_op_type(int(handler.get_argument('op_type')))
        order_time = datetime.datetime.fromtimestamp(
            int(handler.get_argument('order_time'))).strftime('%Y-%m-%d %H:%M:%S')
        price = int(handler.get_argument('code_money'))
        trans_id = self._normalize_trans_id(handler.get_argument('trade_id'), extra)
        uid = self._normalize_uid(handler.get_argument('user_id'), extra)
        product = self._normalize_pid(handler.get_argument('point_id'), extra)
        extra['province'] = handler.get_argument('province_name')

        order_id = gen_order_id()

        order = self.make_order(
            words.ZhongZhiPayTag, order_id, uid, channel, price, words.message_package, product,
            pay_type, ext_data=self._dump_extra(extra), trans_id=trans_id)
        order.success = 1
        order.create_time = order_time

        self.table_cls.raw_sql(
            "select order_id, success from {} where trans_id=%s order by create_time limit 0, 1".format(
                self.table_cls.get_table_name()),
            trans_id,
            callback=partial(self.on_finish_get_order, order, callback))

    @staticmethod
    def transform_op_type(op_type):
        mapping = ('?', 'CMCC', 'CU', 'CT')  # ?,中国移动,中国联通,中国电信
        return mapping[op_type]

    @staticmethod
    def transform_province(p_code):
        mapping = (
            u'北京', u'上海', u'天津', u'重庆', u'河北', u'山西', u'河南', u'辽宁', u'吉林', u'黑龙江',
            u'内蒙古', u'江苏', u'山东', u'安徽', u'浙江', u'福建', u'湖北', u'湖南', u'广东', u'广西',
            u'江西', u'四川', u'海南', u'贵州', u'云南', u'西藏', u'陕西', u'甘肃', u'青海', u'宁夏', u'新疆'
        )
        return mapping[p_code - 10]
