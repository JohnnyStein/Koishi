# -*- coding: utf-8 -*-
from config import DATABASE_NAME

if DATABASE_NAME is None:
    ds_model = None
    DS_TABLE = None
    
    currency_model = None
    CURRENCY_TABLE = None
    
    auto_react_role_model = None
    AUTO_REACT_ROLE_TABLE = None
    
    DB_ENGINE = None
    
else:
    from sqlalchemy.ext.declarative import declarative_base
    from sqlalchemy import Column, Integer, BIGINT, LargeBinary, create_engine, DateTime, String
    from hata.ext.kokoro_sqlalchemy import KOKORO_STRATEGY
    
    BASE = declarative_base()
    
    class ds_model(BASE):
        __tablename__ = 'DS_TABLE'
        id            = Column(BIGINT, primary_key=True)
        user_id       = Column(BIGINT, unique = True)
        position      = Column(Integer)
        data          = Column(LargeBinary(800))
    
    DS_TABLE = ds_model.__table__
    
    class currency_model(BASE):
        __tablename__ = 'CURRENCY'
        id            = Column(BIGINT, primary_key=True)
        user_id       = Column(BIGINT, unique = True)
        total_love    = Column(BIGINT)
        daily_next    = Column(DateTime)
        daily_streak  = Column(Integer)
    
    CURRENCY_TABLE = currency_model.__table__
    
    class auto_react_role_model(BASE):
        __tablename__ = 'AUTO_REACT_ROLE'
        id            = Column(BIGINT, primary_key=True)
        message_id    = Column(BIGINT, unique = True)
        channel_id    = Column(BIGINT)
        data          = Column(LargeBinary(320))
        behaviour     = Column(Integer)
        client_id     = Column(BIGINT)
    
    AUTO_REACT_ROLE_TABLE = auto_react_role_model.__table__
    
    # Creating tables
    DB_ENGINE = create_engine(DATABASE_NAME)
    BASE.metadata.create_all(DB_ENGINE)
    del DB_ENGINE
    
    # Create future engine
    
    DB_ENGINE = create_engine(DATABASE_NAME, strategy=KOKORO_STRATEGY, single_worker=True)
    
    # clearing namespace
    del declarative_base
    del Column
    del Integer
    del DateTime
    del LargeBinary
    del create_engine
