# -*- coding: utf-8 -*-

import inspect
import functools

null = object()


class FakeServerConf(object):
    def __init__(self):
        pass


class FakeRequest(object):
    def __init__(self):
        self.remote_ip = '127.0.0.1'


class FakeHandler(object):
    def __init__(self):
        self.request = FakeRequest()
        self.http_args = {}

    def get_argument(self, key, default=null):
        data = self.http_args.get(key, default)
        if default == null:
            raise KeyError('key:{} not exist.'.format(key))
        return data


def fake_method(has_return=True):
    def wrapper(func):
        @functools.wraps(func)
        def shadow_func(self, *args, **kwargs):
            callback = kwargs.pop('callback', None)
            self._test_data[func.__name__ + "_input"] = list(args) + kwargs.keys() + kwargs.values()
            func(self, *args, **kwargs)
            if callback and has_return:
                callback(self._test_data[func.__name__ + "_output"])
        return shadow_func
    return wrapper


class FakePayOrders(object):
    def __init__(self, *args):
        self.uid = None
        self.order_id = None
        self.trans_id = None
        self.channel = None
        self.success = None
        self.stat = None
        self.price = None
        self.tag = None
        self.ext = None
        self.pkg = None
        self.product = None
        self.create_time = None
        self.visible = None
        self.pay_type = None
        self._test_data = {}

    def get_fields(self):
        fields = []
        for attr in dir(self):
            attr_val = getattr(self, attr)
            if attr.startswith('_') or inspect.ismethod(attr_val) or inspect.isfunction(attr_val):
                continue
            fields.append(attr)
        return fields

    def order_id_len(self):
        return self._test_data.get('order_id_len', 64)

    def uid_len(self):
        return self._test_data.get('uid_len', 32)

    def trans_id_len(self):
        return self._test_data.get('trans_id_len', 64)

    def channel_len(self):
        return self._test_data.get('channel_len', 32)

    def stat_len(self):
        return self._test_data.get('stat_len', 16)

    def product_len(self):
        return self._test_data.get('product_len', 9)

    @fake_method()
    def get_one(self, *args, **kwargs):
        pass

    @fake_method()
    def get_some(self, *args, **kwargs):
        pass

    @fake_method()
    def save(self, *args, **kwargs):
        self._test_data['save'] = self._test_data.get('save', 0) + 1

    @fake_method
    def update_from_db(self, *args, **kwargs):
        fields = self.get_fields()
        test_data = self._test_data.get('update_from_db_data', {})
        for field in fields:
            setattr(self, field, test_data.get(field, None))

    @fake_method(has_return=False)
    def update_to_db(self, *args, **kwargs):
        pass

    @fake_method()
    def raw_sql(self, *args, **kwargs):
        pass
