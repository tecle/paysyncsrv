# -*- coding: utf-8 -*-

import hashlib
import words
import json
import logging
import datetime
from pay.ipay import SmsPayInterface
from functools import partial


class MaiGuangPay(SmsPayInterface):
    def __init__(self, obj, *args):
        super(MaiGuangPay, self).__init__(obj, *args)
        self.success_text = '{"flag":1,"msg":"success"}'
        self.failed_text = '{{"flag":0,"msg":"{}"}}'
        self.key = obj.get('key', '')
        self.need_verify_sign = self.key and obj.get('verify_sign', False)

    def do_biz(self, handler, callback):
        try:
            extra = {}
            req = json.loads(handler.request.body, encoding='utf-8')
            if not self.verify_sign(req):
                return callback(self.failed_text.format('Invalid Sign.')) if callback else None

            trans_id = req['TransactionID']
            order_id = req['SubTransactionID']
            uid = req['IP']
            pay_st = int(req['Status'])
            price = req['MoMoney']
            product = self._normalize_pid(req['GoodsID'], extra)
            channel = req['ChannelID']
            order_time = datetime.datetime.fromtimestamp(int(req['TransactionTime'])).strftime("%Y-%m-%d %H:%M:%S")
            pay_type = self.transform_op_type(int(req['Provider']))

            extra.update({
                'province': self.transform_province(int(req['Province'])),
                'biz_param': req['Ext'],
                'total_money': req['TotalMoney'],
                'valid_money': req['ValidMoney'],
                'sdk_param': req['OID']
            })

            order = self.make_order(
                words.MaiGuangTag, order_id, uid, channel, price,
                words.message_package, product,
                pay_type, ext_data=self._dump_extra(extra), trans_id=trans_id
            )
            order.success = pay_st
            order.create_time = order_time

            self.table_cls.get_one(
                order_id,
                callback=partial(self.on_finish_get_order, order, callback)
            )
        except:
            logging.warning('process callback failed with body:[{}]'.format(handler.request.body))
            raise

    def verify_sign(self, obj):
        if self.need_verify_sign:
            actual_sign = obj.pop('sign')
            keys = obj.keys()
            keys.sort()
            keys.append('SecKey')
            obj['SecKey'] = self.key
            s_to_sign = '&'.join(['{}={}'.format(key, obj[key]) for key in keys])
            logging.debug(s_to_sign)
            expect = hashlib.md5(s_to_sign.encode('utf-8')).hexdigest()
            if expect != actual_sign.lower():
                logging.warning('Invalid sign. expect:{}, actual:{}'.format(expect, actual_sign))
                return False
        return True

    @staticmethod
    def transform_op_type(op_type):
        mapping = ('', 'CMCC', 'CU', 'CT')  # 中国移动,中国联通,中国电信
        return mapping[op_type]

    @staticmethod
    def transform_province(p_code):
        mapping = (
            u'', u'内蒙古', u'贵州', u'江苏', u'安徽', u'山东', u'黑龙江', u'陕西', u'广东', u'广西', u'河南',
            u'宁夏', u'云南', u'湖北', u'西藏', u'河北', u'福建', u'甘肃', u'浙江', u'湖南', u'山西',
            u'江西', u'四川', u'新疆', u'吉林', u'辽宁', u'青海', u'上海', u'海南', u'北京', u'天津', u'重庆'
        )
        return mapping[p_code]
