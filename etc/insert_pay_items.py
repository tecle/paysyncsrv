# coding: utf-8

import time
import os
import sys
import logging
import random
import datetime

cur = os.getcwd()
sys.path.append(os.path.join(cur, '../src'))

from model.order_model import ThirdPayOrders
from main_server import init_db_wrapper
from config_wrapper import ConfigDetail

if __name__ == "__main__":
    logging.basicConfig()

    cfg = ConfigDetail()
    cfg.db_name = 'mimi2_db'
    cfg.db_host = '139.196.148.39'
    cfg.db_user = 'mimi2_user'
    cfg.db_pwd = 'mimi2_111222'
    init_db_wrapper(cfg)

    channel_list = ('baidu', '360', 'taobao', 'yingyongbao')
    tag_list = ('RM', 'FF', 'WM')

    now = time.time()

    for i in xrange(2000):
        o = ThirdPayOrders()
        o.uid = str(random.randint(1, 1230123))
        o.order_id = 'ooo_{}'.format(i)
        o.trans_id = 'ttt_{}'.format(i)
        o.channel = random.choice(channel_list)
        o.success = True
        o.price = random.randint(100, 50000)
        o.tag = random.choice(tag_list)
        o.visible = random.randint(1, 100) > 10
        now += random.randint(-3600*24, 3600*24)
        o.create_time = datetime.datetime.fromtimestamp(now).strftime('%Y-%m-%d %H:%M:%S')
        o.save()
    ThirdPayOrders._thread_pool.shutdown()
