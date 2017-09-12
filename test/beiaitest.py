# -*- coding: utf-8 -*-

from __future__ import absolute_import
import os
import sys
import unittest
from fakeutils import FakeServerConf

sys.path.append(os.path.join(os.getcwd(), "src"))
from pay.beiai import BeiAiPay


class BeiAiTest(unittest.TestCase):
    def test_trans_op_type(self):
        self.assertEqual(u'CMCC', BeiAiPay.transform_op_type(0))
        self.assertEqual(u'CU', BeiAiPay.transform_op_type(1))
        self.assertEqual(u'CT', BeiAiPay.transform_op_type(2))
        with self.assertRaises(IndexError):
            BeiAiPay.transform_op_type(3)

    def test_init_key_not_exist(self):
        obj = {
            "verify_sign": True
        }
        fc = FakeServerConf()
        ba = BeiAiPay(obj, 'domain', fc)
        self.assertTrue(not ba.host_list)
        self.assertFalse(ba.need_verify_sign)

    def test_init_key_exist_not_verify(self):
        obj = {
            "verify_sign": False,
            "key": "123"
        }
        fc = FakeServerConf()
        ba = BeiAiPay(obj, 'domain', fc)
        self.assertTrue(not ba.host_list)
        self.assertFalse(ba.need_verify_sign)

    def test_init(self):
        obj = {
            "verify_sign": True,
            "key": "123"
        }
        fc = FakeServerConf()
        ba = BeiAiPay(obj, 'domain', fc)
        self.assertTrue(not ba.host_list)
        self.assertTrue(ba.need_verify_sign)

if __name__ == "__main__":
    unittest.main().runTests()
