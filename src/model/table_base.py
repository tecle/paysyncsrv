# coding:utf-8

import inspect
import logging
from model.db_wrapper import get_conn_pool

from tornado.concurrent import run_on_executor
from collections import namedtuple

Wanted = namedtuple('Wanted', ['attr'])


class TableBase(object):
    __primary_key__ = 'id'
    __fields_cache__ = {}
    __slots__ = []

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def get_table_name(cls):
        return cls.__name__

    def get_fields(self):
        table_name = self.get_table_name()
        if table_name in self.__fields_cache__:
            return self.__fields_cache__[table_name]
        self.__fields_cache__[table_name] = fields = []
        for attr in dir(self):
            attr_val = getattr(self, attr)
            if attr.startswith('_') or inspect.ismethod(attr_val) or inspect.isfunction(attr_val):
                continue
            fields.append(attr)
        return fields

    def parse_from_sql_response(self, response):
        fields = self.get_fields()
        for field in fields:
            setattr(self, field, response.get(field, None))
        return self

    @classmethod
    @run_on_executor(executor='_thread_pool', io_loop='_io_loop')
    def get_one(cls, target_value, target_field=None):
        if not target_field:
            target_field = cls.__primary_key__
        query = 'select * from %s where %s=%%s' % (cls.get_table_name(), target_field)
        res = get_conn_pool().get(query, target_value)
        if not res:
            return None
        return cls().parse_from_sql_response(res)

    @classmethod
    @run_on_executor(executor='_thread_pool', io_loop='_io_loop')
    def get_some(cls, condition, limit=None, *args):
        '''
        :param condition: str for condition
        :param limit: (start, size)
        :param args: condition args
        :return:
        '''
        if not limit:
            query = 'select * from %s where %s' % (cls.get_table_name(), condition)
        else:
            query = 'select * from %s where %s limit %s' % \
                    (cls.get_table_name(), condition,
                     '%d' % limit if isinstance(limit, int) else '%d, %d' % (limit[0], limit[1]))
        sql_res = get_conn_pool().query(query, *args)
        res = []
        if sql_res is None:
            return True, res
        for item in sql_res:
            inst = cls()
            inst.parse_from_sql_response(item)
            res.append(inst)
        return True, res

    @run_on_executor(executor='_thread_pool', io_loop='_io_loop')
    def save(self):
        logging.debug('save to db...')
        fields, values = [], []
        for field in self.get_fields():
            if getattr(self, field) is not None:
                fields.append(field)
                values.append(getattr(self, field))
        query = 'insert into %s (%s) values (%s)' % \
                (self.get_table_name(), ','.join(fields), ','.join(['%s'] * len(fields)))
        return get_conn_pool().insert(query, *values)

    @run_on_executor(executor='_thread_pool', io_loop='_io_loop')
    def update_to_db(self):
        fields, values = [], []
        pk = self.__primary_key__
        for field in self.get_fields():
            if getattr(self, field) is not None and field != pk:
                fields.append(field)
                values.append(getattr(self, field))
        if not fields:
            # 没有数据更新
            return
        query = 'update %s set %s where %s=%%s' % \
                (self.get_table_name(), ','.join(['%s=%%s' % item for item in fields]), pk)
        values.append(getattr(self, pk))
        get_conn_pool().update(query, *values)

    @run_on_executor(executor='_thread_pool', io_loop='_io_loop')
    def update_from_db(self):
        '''
        update Wanted field from database.
        notice: make sure you have set primary key's value before update from db.
        :return: boolean(success/fail)
        '''
        fields = [field for field in self.get_fields() if getattr(self, field) == Wanted]
        pk_val = getattr(self, self.__primary_key__)
        assert pk_val is not None and pk_val != Wanted
        query = 'select %s from %s where %s=%%s' % (
            ','.join(fields), self.get_table_name(), self.__primary_key__)
        res = get_conn_pool().get(query, pk_val)
        if not res:
            return False
        for k, v in res.items():
            setattr(self, k, v)
        return True

    @classmethod
    @run_on_executor(executor='_thread_pool', io_loop='_io_loop')
    def raw_sql(cls, sql, *args):
        res = get_conn_pool().query(sql, *args)
        return [cls().parse_from_sql_response(row) for row in res] if res else []

    def __str__(self):
        return ','.join(('%s=%s' % (key, getattr(self, key)) for key in self.get_fields()))
