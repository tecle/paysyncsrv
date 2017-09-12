# coding: utf-8

import os
import time
import json
import urllib
import hashlib
import commands
import unittest
from tornado.httpclient import HTTPClient
from tornado.httpclient import HTTPRequest

CUR_PATH = os.path.split(os.path.realpath(__file__))[0]

server = 'pay.leeqo.cn:8080'
# server = 'localhost:5007'

case_cache = {}


class TestCase(unittest.TestCase):
    @staticmethod
    def _ctrl_encode(op, biz_params):
        if 'ctrl_api_key' not in case_cache:
            key = commands.getoutput('cd {} && grep "__sign_key__ =" ctrl_handlers.py |awk -F= \'{{print $2}}\''
                                     .format(os.path.join(CUR_PATH, '../src/handlers'))).strip().replace('\'', '')
            case_cache['ctrl_api_key'] = key
        ts = int(time.time())
        keys = biz_params.keys()
        keys.sort()
        str_to_sign = \
            "{}&{}&{}&{}".format(op, ts, '&'.join([biz_params[key] for key in keys]), case_cache['ctrl_api_key'])
        biz_params['op'] = op
        biz_params['ts'] = ts
        biz_params['sign'] = hashlib.md5(str_to_sign).hexdigest()
        return urllib.urlencode(biz_params)

    def _request(self, url, body, method='POST'):
        client = HTTPClient()
        req = HTTPRequest(url, method=method, body=body)
        rsp = client.fetch(req, raise_error=False)
        return rsp.code, rsp.body, rsp.reason

    def _assert_common_order(self, order_id, expected_price, expected_channel, expected_code=200, expected_msg=''):
        code, body, reason = self._request(
            "http://{}/mimi2/oq".format(server), 'oid=' + order_id)
        self.assertEqual(200, code, reason)
        obj = json.loads(body)
        self.assertDictContainsSubset({
            'code': expected_code,
            'msg': expected_msg,
            'price': expected_price,
            'channel': expected_channel
        }, obj, body)

    def test_rongmeng_callback(self):
        params = {
            "return_code": 200,
            "totalFee": 100,
            "channelOrderId": "oid_{}".format(int(time.time() * 1000)),
            "orderId": "trans_{}".format(int(time.time()) * 1000),
            "timeStamp": int(time.time()),
            "attach": "cn001,user001,pro001,pkg001",
            "transactionId": "66666"
        }
        str_to_sign = 'channelOrderId={0}&orderId={1}&timeStamp={2}&totalFee={3}'.format(
            params['channelOrderId'], params['orderId'], params['timeStamp'], params['totalFee']
        )
        params['sign'] = hashlib.md5(str_to_sign).hexdigest()
        code, body, reason = self._request(
            "http://{}/mimi2/rmcb?{}".format(server, urllib.urlencode(params)), None, method='GET')
        self.assertEqual(200, code, reason)
        self.assertEqual('SUCCESS', body)
        self._assert_common_order(params['channelOrderId'], 100, 'cn001')

    def test_fafa_callback(self):
        fafa_json = {
            "Error": 1,
            "Message": "success",
            "MchId": "100001",
            "MchTradeNo": "trans_{}".format(int(time.time()) * 1000),
            "OutTradeNo": "oid_{}".format(int(time.time() * 1000)),
            "TradeAttach": "cn001,fafa1,fpro001,f.fb.fc",
            "ActuallyMoney": 100,
            "TimeEnd": int(time.time()),
        }

        key = commands.getoutput('cd {} && grep "__fafa_key__ =" fafapay_handler.py |awk -F= \'{{print $2}}\''.format(
            os.path.join(CUR_PATH, '../src/handlers')
        )).strip().replace('\'', '')

        str_to_sign = u'{}{}{}{}{}{}{}{}{}'.format(
            fafa_json['Error'],
            fafa_json['Message'] or '',
            fafa_json['MchId'],
            fafa_json['MchTradeNo'],
            fafa_json['OutTradeNo'],
            fafa_json['TradeAttach'],
            fafa_json['ActuallyMoney'],
            fafa_json['TimeEnd'],
            key
        )
        fafa_json['Sign'] = hashlib.md5(str_to_sign.encode('utf-8')).hexdigest()
        code, body, reason = self._request(
            'http://{}/mimi2/ffcb'.format(server), json.dumps(fafa_json))
        self.assertEqual(200, code)
        self.assertEqual('success', body)
        self._assert_common_order(fafa_json['OutTradeNo'], 100, 'cn001')

    def test_set_deduct(self):
        code, body, reason = self._request('http://{}/mimi2/ctrl'.format(server),
                                           self._ctrl_encode('DEDUCT', {'cid': 'cn001', 'dr': '100.00'}))
        self.assertEqual(200, code, reason)
        self.assertEqual('OK', body)

    def test_prepay(self):
        code, body, reason = self._request(
            "http://{}/mimi2/cpp".format(server), "uid=test_user&cid=tc001&sdk=FF&price=100")
        self.assertEqual(200, code)
        obj = {}
        try:
            obj = json.loads(body)
        except ValueError:
            self.assertTrue(False, body)
        self.assertTrue('cb' in obj, body)
        self.assertTrue('order' in obj, body)


if __name__ == "__main__":
    runner = unittest.TextTestRunner()
    suit = unittest.TestSuite()
    suit.addTest(unittest.makeSuite(TestCase, 'test'))
    runner.run(suit)
