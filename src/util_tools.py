# coding:utf-8
from pyDes import *
import time
import words


class SingletonBase(type):
    def __init__(cls, name, bases, dict):
        super(SingletonBase, cls).__init__(name, bases, dict)
        cls._instance = None

    def __call__(cls, *args, **kw):
        if cls._instance is None:
            cls._instance = super(SingletonBase, cls).__call__(*args, **kw)
        return cls._instance


# key = H74S0Dd2
def des_decoder(des_str, key="H74S0Dd2", hex_decode=True):
    des_str = des_str.decode('hex')
    k = des(key, CBC, key, pad=None, padmode=PAD_PKCS5)
    return k.decrypt(des_str)


def des_encoder(ipt, key="Happywrd", hex_encode=True):
    k = des(key, CBC, key, pad=None, padmode=PAD_PKCS5)
    s = k.encrypt(ipt)
    return s.encode('hex') if hex_encode else s


def url_decoder(s):
    ret = {}
    for item in ((i[:i.find('=')], i[i.find('=') + 1:]) for i in s.split("&")):
        ret[item[0]] = item[1]
    return ret


def simple_cache(expired_time=3):
    def decorator(func):
        cache = {}

        def f(self, key):
            if key in cache and time.time() - cache[key]['ts'] < expired_time:
                return cache[key]['val']
            else:
                cache[key] = {}
            cache[key]['ts'] = time.time()
            cache[key]['val'] = func(self, key)
            return cache[key]['val']

        return f

    return decorator


def gen_order_id(tag=None):
    return str(int(time.time() * 1000000))
