import logging
import os
import sys
from string import Template

import tornado.concurrent
import tornado.ioloop
import tornado.web
from tornado.options import define, options

CUR_PATH = os.getcwd()
COMMON_CONFIG_FILE = os.path.join(CUR_PATH, "confs/server.cfg")
PAY_CONFIG_FILE = os.path.join(CUR_PATH, 'confs/pay_conf.json')
VIEWS_DIR = os.path.join(CUR_PATH, "src/views")

sys.path.append(CUR_PATH)

from config_wrapper import ConfigDetail, ServerConf
from handlers.mimi2_handler import Mimi2CallbackHandler
from handlers.mimi2_handler import Mimi2Handler
from handlers.mimi2_handler import Mimi2QueryOrderHandler
from handlers.mimi2_handler import Mimi2UserHandler
import handlers.wiipay_handler as wiipay
import handlers.rongmeng as RoMen
import handlers.wmpay_handler as WiMi
import handlers.common_handlers as CommonHandler
import handlers.fafapay_handler as FafaPay
import handlers.ctrl_handlers as CtrlHandler
import handlers.sunpay_handler as SunHandler
from model.db_wrapper import get_conn, get_conn_pool
from pay.pay_base import PayFactory


# Global params
g_app = None


def stop_server():
    tornado.ioloop.IOLoop.instance().stop()


def parse_server_conf():
    parser = ConfigDetail()
    if not parser.parse(COMMON_CONFIG_FILE):
        print ("Parse config file [%s] failed." % COMMON_CONFIG_FILE)
        exit(1)
    return parser


def init_db_wrapper(cfg):
    from model.table_base import TableBase
    from concurrent.futures import ThreadPoolExecutor
    setattr(TableBase, '_io_loop', tornado.ioloop.IOLoop.instance())
    setattr(TableBase, '_thread_pool', ThreadPoolExecutor(12))
    get_conn_pool(cfg)


def start_server(server_port, enable_debug):
    global g_app

    cfg = parse_server_conf()
    if cfg.port:
        server_port = cfg.port

    cur_ip = cfg.domain

    routine_table = [
        (r"/mimi2/query", Mimi2Handler),
        (r"/mimi2/queryuser", Mimi2UserHandler),
        (r"/mimi2/callback", Mimi2CallbackHandler),
        (r"/mimi2/queryorder", Mimi2QueryOrderHandler),

        (r"/mimi2/rmcb", RoMen.RongmengNotifyHandler),
        (r"/mimi2/rmpayst", RoMen.RongmengPayStatQueryHandler),
        (r"/mimi2/rmuif", RoMen.RongmengQueryHandler),

        (r"/mimi2/orders", CommonHandler.GetUserOrdersHandler),
        (r"/mimi2/oq", CommonHandler.GetOrderInfoHandler),
        (r"/mimi2/cpp", CommonHandler.PrepayHandler),
        (r"/mimi2/cb/(.*)$", CommonHandler.CommonCallback),
        (r"/mimi2/ok", CommonHandler.SuccessHandler),
        (r"/mimi2/ctrl", CtrlHandler.CtrlHandler),

        (r"/mimi2/ffcb", FafaPay.FfCallbackHandler),

        (r"/mimi2/wmcb", WiMi.WmCallbackHandler),
        (r"/mimi2/wmp", WiMi.WmPrepayHandler),
        (r"/mimi2/wmif", WiMi.WmOrderStatusHandler),
        (r"/mimi2/wmq", WiMi.WmQueryHandler),

        (r"/mimi2/sunq", SunHandler.QueryToRemoteHandler),
        (r"/mimi2/sunp", SunHandler.SunPrePayHandler),
        (r"/mimi2/suncb", SunHandler.SunPayCallbackHandler),
        (r"/wii/callback", wiipay.WiiHandlerV2),
        (r"/wii/query", wiipay.WiiQueryHandlerV2)
    ]

    if not cur_ip:
        logging.fatal('start server failed.')
        return

    init_db_wrapper(cfg)
    server_conf = ServerConf()
    if not enable_debug and not server_conf.init_conf():
        logging.fatal('init deduct conf failed.')
        return
    g_app = tornado.web.Application(
        routine_table,
        db_inst=get_conn(cfg),
        server_ip=cur_ip,
        domain=cur_ip,
        routine_info=routine_table,
        server_conf=server_conf,
        pay_conf=PayFactory(PAY_CONFIG_FILE, cur_ip, server_conf)
    )
    g_app.listen(server_port, address='127.0.0.1', xheaders=True)
    logging.info("starting server on port[{}]".format(server_port))
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    define("port", 5007, help="Server listen port", type=int)
    define("debug", False, help="Use debug mode", type=bool)
    # if we use parse_command_line,
    # then log-to-stderr config in logging_config file will not take effect
    default_params = {
        '--log-to-stderr': 'true',
        '--log_file_prefix': os.path.join(CUR_PATH, 'logs/pay.log'),
        '--logging': 'debug',
        '--log_file_num_backups': '3'
    }
    sys.argv += ['%s=%s' % (k, v) for k, v in default_params.items()]

    options.parse_command_line()
    start_server(options.port, options.debug)
