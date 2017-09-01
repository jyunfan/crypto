import time
import datetime
import logging
import queue
import threading

import requests

#logging.basicConfig() 
#logging.getLogger().setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

#requests_log = logging.getLogger("requests.packages.urllib3")
#requests_log.setLevel(logging.DEBUG)
#requests_log.propagate = True


hour_hist = {}
day_hist = {}
update_queue = queue.Queue()

def get_coin_list():
    URL = 'https://www.cryptocompare.com/api/data/coinlist/'
    rsp = requests.get(URL, timeout=2).json()
    coin_list = rsp['Data'].keys()
    return coin_list


def get_hist_data(period, fsym, tsym):
    URL_MIN = 'https://min-api.cryptocompare.com/data/histominute?fsym=%s&tsym=%s&limit=60' % (fsym, tsym)
    URL_HOUR = 'https://min-api.cryptocompare.com/data/histohour?fsym=%s&tsym=%s&limit=2' % (fsym, tsym)
    URL_DAY = 'https://min-api.cryptocompare.com/data/histoday?fsym=%s&tsym=%s&limit=1' % (fsym, tsym)
    if period == 'min':
        rsp = requests.get(URL_MIN, timeout=2).json()['Data']
    elif period == 'hour':
        rsp = requests.get(URL_HOUR, timeout=2).json()['Data']
    elif period == 'day':
        rsp = requests.get(URL_DAY, timeout=2).json()['Data']

    return rsp


def get_exchange_pairs():
    URL = 'https://bittrex.com/api/v1.1/public/getmarkets'

    logger.info('Get all pairs from bittrex')
    rsp = requests.get(URL, timeout=2).json()['result']
    pairs = []
    for pair in rsp:
        pairs.append((pair['MarketCurrency'], pair['BaseCurrency']))
    return pairs


def update_data(coin):
    global hour_hist
    global day_hist
    now = datetime.datetime.now().timestamp()

    daydata = day_hist.get(coin, None)
    if daydata is None or daydata[-1]['time'] - now > 24*60*60:
        logger.info('Update %s' % coin)
        day_hist[coin] = get_hist_data('day', coin, 'BTC')
        time.sleep(5)


    hourdata = hour_hist.get(coin, None)
    if hourdata is None or hourdata[-1]['time'] - now > 60*60:
        logger.info('Update %s' % coin)
        hour_hist[coin] = get_hist_data('hour', coin, 'BTC')
        time.sleep(5)
        update_queue.put(coin)
    else:
        # no new data
        return


def loop_market():
    pairs = get_exchange_pairs()
    coins = get_coin_list()

    valid_coins = []
    for pair in pairs:
        fsym, tsym = pair
        if tsym != 'BTC':
            continue
        if fsym in coins:
            valid_coins.append(fsym)
        else:
            logger.info(fsym + ' not in data source')
    logger.info('Check %d coins' % len(valid_coins))


    while True:
        for coin in valid_coins:
            update_data(coin)


def loop_execute():
    while True:
        print('do some work')
        time.sleep(3)


if __name__ == '__main__':
    t = threading.Thread(target=loop_market)
    t.start()
    t = threading.Thread(target=loop_execute)
    t.start()

