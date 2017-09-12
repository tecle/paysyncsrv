# coding:utf-8

import torndb

import logging
import threading
import Queue

MYSQL_POOL = None
MYSQL_CONN = None


def get_conn_pool(cfg=None):
    global MYSQL_POOL
    if MYSQL_POOL is None:
        db_cfg = cfg
        MYSQL_POOL = MysqlConnPool(
            db_cfg.db_host, db_cfg.db_name, db_cfg.db_user, db_cfg.db_pwd)
    return MYSQL_POOL


def get_conn(cfg=None):
    global MYSQL_CONN
    if MYSQL_CONN is None:
        db_cfg = cfg
        MYSQL_CONN = torndb.Connection(
            db_cfg.db_host, db_cfg.db_name, db_cfg.db_user, db_cfg.db_pwd, time_zone="+8:00")
    return MYSQL_CONN


class MysqlConnPool(object):
    def __init__(self, host, database, user, pwd, max_conns=30):
        self.idle_conn = Queue.Queue()
        self.pool_size = 0
        self.max_conns = max_conns
        self.conn_params = (host, database, user, pwd)
        self.poll_size_mutex = threading.Lock()

    def __del__(self):
        for i in range(self.pool_size):
            try:
                conn = self.idle_conn.get(timeout=5)
                conn.close()
            except Exception:
                logging.warning('Close conn failed.ignore.')

    def come_back(self):
        logging.info('return one connection to poll')
        return self.idle_conn.get()

    def _get_conn_from_pool(self):
        if self.idle_conn.empty() and self.pool_size < self.max_conns:
            conn = torndb.Connection(*self.conn_params, time_zone="+8:00")
            self.poll_size_mutex.acquire()
            self.pool_size += 1
            self.poll_size_mutex.release()
        else:
            conn = self.idle_conn.get()
        return conn

    def get(self, *args, **kwargs):
        conn = self._get_conn_from_pool()
        return self._safe_sql(conn, conn.get, *args, **kwargs)

    def query(self, *args, **kwargs):
        conn = self._get_conn_from_pool()
        return self._safe_sql(conn, conn.query, *args, **kwargs)

    def update(self, *args, **kwargs):
        conn = self._get_conn_from_pool()
        return self._safe_sql(conn, conn.update, *args, **kwargs)

    def insert(self, *args, **kwargs):
        conn = self._get_conn_from_pool()
        return self._safe_sql(conn, conn.insert, *args, **kwargs)

    def _safe_sql(self, conn, method, *args, **kwargs):
        res = None
        try:
            res = method(*args, **kwargs)
        except Exception:
            res = None
            logging.exception('exec sql failed with args[{}] and kwargs[{}].'.format(args, kwargs))
        finally:
            self.idle_conn.put(conn)
            return res
