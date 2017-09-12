# coding: utf-8

class WiiOrderModel(object):
    def __init__(self, db):
        self.db = db
        self.params = {
            "operatorType": "",
            "operatorTypeTile": "",
            "channelCode": "",
            "appCode": "",
            "payCode": "",
            "imsi": "",
            "tel": "",
            "state": "",
            "bookNo": "",
            "date": "",
            "price": 0,
            "synType": "",
            "devPrivate": ""
        }

    def save(self):
        values = ['%%(%s)s' % k for k in self.params]
        query = "insert into wii_orders (%s) values (%s)" %\
                (','.join(self.params.keys()), ','.join(values))
        self.db.insert(query, **self.params)

    @staticmethod
    def get_user_cost(db, uid):
        query = "select price from wii_orders where uid=%s"
        ret = db.query(query, uid)
        cost = 0
        for item in ret:
            cost = max(cost, item["price"])
        return cost

    @staticmethod
    def exist(db, bookNo = None):
        if not bookNo:
            return True
        query = "select * from wii_orders where bookNo=%s"
        ret = db.get(query, bookNo)
        return ret is not None

    @staticmethod
    def get_order_status(db, bookNo = None):
        if not bookNo:
            return None
        query = "select state from wii_orders where bookNo=%s"
        ret = db.get(query)
        return ret['state'] if ret else None


if __name__ == "__main__":
    def f(query, **kwargs):
        print query
        print kwargs
        print len(kwargs)

    db = WiiOrderModel(None)
    setattr(db, "insert", f)
    WiiOrderModel(db).save()    
