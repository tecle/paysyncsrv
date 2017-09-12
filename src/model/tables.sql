create table CommonOrders(
    order_id char(64) primary key,
    uid char(64) not null,
    trans_id char(64) not null,
    stat char(16) default '',
    tag char(2) not null,
    price int not null,
    other text,
    create_time timestamp default CURRENT_TIMESTAMP
)CHARACTER SET utf8mb4;

create table ThirdPayOrders(
    order_id char(64) primary key,
    uid char(32) not null,
    trans_id char(64) default '',
    channel char(32) not null,
    success tinyint(1) default 0,
    stat char(16) default '',
    product char(8) default'',
    price int not null,
    pkg varchar(128) default '',
    tag char(6) not null,
    visible tinyint default 0,
    pay_type char(8) default 'UNKNOWN',
    ext text,
    create_time timestamp default CURRENT_TIMESTAMP
)CHARACTER SET utf8mb4;


create table SmsPayOrders(
    order_id char(64) primary key,
    uid char(32) not null,
    trans_id char(64) default '',
    channel char(32) not null,
    success tinyint(1) default 0,
    stat char(16) default '',
    product char(8) default'',
    price int not null,
    pkg varchar(128) default '',
    tag char(6) not null,
    visible tinyint default 0,
    pay_type char(8) default 'UNKNOWN',
    ext text,
    create_time timestamp default CURRENT_TIMESTAMP
)CHARACTER SET utf8mb4;


create table orders(
    _id int auto_increment primary key,
    uid char(48) default '',
    app_key char(32) default '',
    txn_seq char(32) default '',
    order_id char(32) default '',
    rsp_code char(6) default '',
    txn_time char(14) default '',
    actual_txn_amt int default 0,
    time_stamp char(20) default 0,
    create_time timestamp default CURRENT_TIMESTAMP
)CHARACTER SET utf8mb4;

create table wii_orders(
    _id int auto_increment primary key,
    operatorType char(12),
    operatorTypeTile varchar(32),
    channelCode varchar(32),
    appCode varchar(32),
    payCode varchar(64),
    imsi varchar(64),
    tel varchar(18),
    state char(20),
    bookNo varchar(32),
    date varchar(16),
    price int(11),
    synType char(16),
    devPrivate varchar(255),
    create_time timestamp default CURRENT_TIMESTAMP,
    uid char(32)
)CHARACTER SET utf8mb4;