# coding: utf-8
import logging
from util_tools import SingletonBase
from model.db_wrapper import get_conn_pool
import json
import random


class ServerConf(object):
    MaxPoint = 10000

    '''这里的pay_type使用标准支付方式'''
    def __init__(self):
        self.pay_type_conf = {}
        self.deduct_conf = {}
        self.max_deduct_level = 0

    @staticmethod
    def validate_pay_method(pay_method):
        return pay_method in ('W', 'A')

    def get_pay_type_by_tag(self, sdk, pay_method):
        '''
        :param sdk: ie. SUN
        :param pay_method: ie. W/A
        :return: W.app if exist else None.
        '''
        pay_type = self.pay_type_conf.get(sdk, {}).get(pay_method, None)
        return "{}.{}".format(pay_method, pay_type) if pay_type else None

    def switch_pay_type(self, tag, pay_type):
        '''
        :param tag: sdk name
        :param pay_type: ie. W.app --> 'W': 'app'
        :return:
        '''
        pay_detail = pay_type.split('.')
        self.pay_type_conf.setdefault(tag, {})[pay_detail[0]] = pay_detail[1]

    def _init_pay_type_conf(self):
        '''
        {
          "SUN": {
            "W": "app"
          }
        }
        '''
        res = get_conn_pool().query('select sdk,mode_opt from tb_pay_mode')
        if res is None:
            logging.fatal('cannot get pay type conf from table tb_pay_mode')
            return False
        for item in res:
            sdk = item['sdk']
            pay_type = item['mode_opt'].split('.')
            if sdk not in self.pay_type_conf:
                self.pay_type_conf[sdk] = {}
            self.pay_type_conf[sdk][pay_type[0]] = pay_type[1]
        logging.info('pay type conf:{}'.format(json.dumps(self.pay_type_conf, indent=2)))
        return True

    @staticmethod
    def parse_deduct_ratio(raw_str):
        if not raw_str:
            return []
        return [int(float(item) * 100) for item in raw_str.split(',')]

    def _init_deduct_conf(self):
        res = get_conn_pool().query('select channel_id,deduct_ratio from tb_app_channel')
        if res is None:
            logging.fatal('cannot get deduct conf from table tb_app_channel')
            return False
        for item in res:
            dr = self.parse_deduct_ratio(str(item['deduct_ratio']))
            self.deduct_conf[item['channel_id']] = dr
            self.max_deduct_level = max(self.max_deduct_level, len(dr))
        logging.info('Channel conf:\n{}'.format(
            json.dumps({k: v for k, v in self.deduct_conf.items() if [i for i in v if i > 0]}, indent=2)))
        return True

    def init_conf(self):
        return self._init_deduct_conf() and self._init_pay_type_conf()

    def may_deduct(self, channel_id):
        vl = 0
        df = self.deduct_conf.get(channel_id, tuple())
        for item in df:
            if random.randint(0, self.MaxPoint) >= item:
                vl += 1
            else:
                break
        if not df:
            vl = self.max_deduct_level
        return vl

    def modify_deduct(self, channel_id, vals_str):
        new_val = [int(float(item) * 100) for item in vals_str.split(',')]
        for val in new_val:
            if val < 0 or val > self.MaxPoint:
                logging.warning('invalid deduct rate[{}]'.format(new_val))
                return False
        self.max_deduct_level = max(self.max_deduct_level, len(new_val))
        self.deduct_conf[channel_id] = new_val
        return True

    def parse_conf(self, s):
        try:
            obj = json.loads(s)
        except Exception:
            logging.exception('load deduct conf string [{}] failed.'.format(s))
            return False
        self.deduct_conf = obj
        return True


class ConfigDetail(object):
    __metaclass__ = SingletonBase

    def parse(self, cfg_file_path):
        with open(cfg_file_path, "rb") as f:
            cfg_ctnt = f.read()
        if cfg_ctnt is None:
            logging.error("Read file failed.")
            return False
        logging.info("Cfg file content:%s" % cfg_ctnt)
        kv_map = {}
        for line in cfg_ctnt.split("\n"):
            line = line.strip()
            if len(line) == 0 or line.startswith("#"):
                continue
            pos = line.find("=")
            if pos < 0:
                continue
            key = line[0:pos].strip()
            val = line[pos + 1:].strip()
            kv_map[key] = val
        logging.info("After parse:%s" % kv_map)
        return self._extratInfo(kv_map)

    def _extratInfo(self, kv_map):
        self.db_host = "%s:%s" % (kv_map.get("db.host", "127.0.0.1"),
                                  kv_map.get("db.port", "3306"))
        try:
            self.db_name = kv_map["db.name"]
            self.db_user = kv_map["db.user"]
            self.db_pwd = kv_map["db.password"]
            self.domain = kv_map['domain']
            self.port = int(kv_map.get('server.port', 0))
        except Exception:
            logging.exception("Get param error")
            return False
        return True
