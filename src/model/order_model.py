# coding: utf-8
import time

from model import table_base


class ThirdPayOrders(table_base.TableBase):
    __primary_key__ = "order_id"

    __slots__ = [
        'uid', 'order_id', 'trans_id', 'channel', 'stat', 'pkg', 'visible',
        'price', 'tag', 'ext', 'success', 'product', 'create_time', 'pay_type'
    ]

    def __init__(self, **kwargs):
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
        super(ThirdPayOrders, self).__init__(**kwargs)

    @staticmethod
    def order_id_len():
        return 64

    @staticmethod
    def uid_len():
        return 32

    @staticmethod
    def trans_id_len():
        return 64

    @staticmethod
    def channel_len():
        return 32

    @staticmethod
    def stat_len():
        return 16

    @staticmethod
    def product_len():
        return 8


class SmsPayOrders(ThirdPayOrders):
    def __init__(self, **kwargs):
        super(SmsPayOrders, self).__init__(**kwargs)


class CommonOrders(table_base.TableBase):
    __primary_key__ = "order_id"

    def __init__(self, **kwargs):
        self.uid = None
        self.order_id = None
        self.trans_id = None
        self.price = None
        self.stat = None
        self.tag = None
        self.other = None
        super(CommonOrders, self).__init__(**kwargs)


class OrderModel:
    def __init__(self, db):
        self.db = db
        self.fields = []

    def initFromObj(self, obj):
        for key, val in obj.items():
            setattr(self, key, val)
            self.fields.append(key)

    def setUid(self, uid):
        self.uid = uid

    def setOrderId(self, oid):
        self.order_id = oid

    def isDuplicate(self):
        query = "select _id from orders where order_id=%s"
        return self.db.get(query, self.order_id) is not None

    def add(self):
        query = "insert into orders" \
                " (uid, app_key, txn_seq, order_id, rsp_code," \
                " txn_time, actual_txn_amt, time_stamp)" \
                "values(%s, %s, %s, %s, %s, %s, %s, %s)"
        self.db.insert(query, self.uid, self.app_key, self.txn_seq, self.order_id,
                       self.rsp_code, self.txn_time, self.actual_txn_amt, self.time_stamp)

    def getPayed(self):
        query = "select actual_txn_amt from orders where uid=%s"
        ret = self.db.query(query, self.uid)
        if not ret:
            return None
        m = 0
        for item in ret:
            m = max(m, int(item["actual_txn_amt"]))
        return m

    def getOrderStatus(self):
        query = "select rsp_code from orders where order_id=%s"
        ret = self.db.get(query, self.order_id)
        if ret is not None:
            return ret['rsp_code']
        return None

    def delete(self):
        query = "delete from orders where uid=%s"
        self.db.execute(query, self.uid)


if __name__ == "__main__":
    import torndb

    db = torndb.Connection("127.0.0.1:3306", "mimi2_db", "test_user", "test_pw")
    om = OrderModel(db)
    # test add
    uobj = {'uid': '923'}
    robj = {'app_key': '1', 'txn_seq': '2', 'order_id': '3', 'rsp_code': '4',
            'txn_time': '5', 'actual_txn_amt': '6', 'time_stamp': '7'}
    om.initFromObj(uobj)
    om.initFromObj(robj)
    om.add()
