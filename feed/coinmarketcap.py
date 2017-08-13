import os
import time
import requests
import logging
#import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(filename='coinmarketcap.log',level=logging.DEBUG, format=FORMAT)
logger = logging.getLogger(__name__)

Base = declarative_base()
 
class Ticker(Base):
    __tablename__ = 'ticker'
    # Here we define columns for the table person
    # Notice that each column is also a normal Python instance attribute.
    id = Column(String, primary_key=True)
    name = Column(String)
    symbol = Column(String)
    rank = Column(Integer)
    price_usd = Column(Float)
    price_btc = Column(Float)
    volume_usd_24h = Column(Integer)
    market_cap_usd = Column(Integer)
    available_supply = Column(Integer)
    total_supply = Column(Integer)
    percent_change_1h = Column(Float)
    percent_change_24h = Column(Float)
    percent_change_7d = Column(Float)
    last_updated = Column(Integer)


def get_ticker():
    url = 'https://api.coinmarketcap.com/v1/ticker/'
    data = requests.get(url, timeout=3).json()
    ticker = []

    for entry in data:
        try:
            t = Ticker(
                id = entry['id'],
                name = entry['name'],
                symbol = entry['symbol'],
                rank = int(entry['rank']),
                price_usd = float(entry['price_usd']),
                price_btc = float(entry['price_btc']),
                volume_usd_24h = float(entry['24h_volume_usd']),
                market_cap_usd = int(float(entry['market_cap_usd'])),
                available_supply = int(float(entry['available_supply'])),
                total_supply = int(float(entry['total_supply'])),
                percent_change_1h = float(entry['percent_change_1h']),
                percent_change_24h = float(entry['percent_change_24h']),
                percent_change_7d = float(entry['percent_change_7d']) if entry['percent_change_7d'] is not None else None,
                last_updated = int(entry['last_updated'])
                )

            ticker.append(t)
        except:
            pass
    return ticker


def get_engine():
    if not os.path.exists('coinmarketcap.db'):
        engine = create_engine('sqlite:///coinmarketcap.db')
        engine.execute('''CREATE TABLE ticker
            (id TEXT,
            name TEXT,
            symbol TEXT,
            rank INTEGER,
            price_usd REAL,
            price_btc REAL,
            volume_usd_24h INTEGER,
            market_cap_usd INTEGER,
            available_supply INTEGER,
            total_supply INTEGER,
            percent_change_1h REAL,
            percent_change_24h REAL,
            percent_change_7d REAL,
            last_updated INTEGER,
            PRIMARY KEY (id, last_updated))
                  ''')
    else:
        engine = create_engine('sqlite:///coinmarketcap.db')

    return engine

def main():
    engine = get_engine()
    Base.metadata.create_all(engine)
    Base.metadata.bind = engine
    DBSession = sessionmaker(bind=engine)
    session = DBSession()

    while True:
        try:
            logger.info('Get tickers')
            tickers = get_ticker()
            logger.info('Found %d symbols' % len(tickers))
        except:
            pass

        added = 0
        for t in tickers:
            try:
                if session.query(Ticker).filter_by(id = t.id, last_updated=t.last_updated).first() != None:
                    continue
                session.add(t)
                session.commit()
                added += 1
            except:
                logger.error(sys.exc_info()[0])
                pass
        logger.info('Add %d symbols' % added)

        time.sleep(120)


if __name__ == '__main__':
    main()
