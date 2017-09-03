import time
import datetime
import logging
import queue
import threading

import requests
import numpy as np

import bittrex

#logging.basicConfig() 
#logging.getLogger().setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler = logging.FileHandler('crypto.log')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

#requests_log = logging.getLogger("requests.packages.urllib3")
#requests_log.setLevel(logging.DEBUG)
#requests_log.propagate = True

global account

POSITION_IN_BTC = 0.01
PRICE_UP_MIN = 1.05
PRICE_UP_MAX = 1.15
PRICE_DOWN_THRESH = 0.95
VOL_UP_RATIO_THRESH = 2
VOL_UP_THRESH = 10
VOL_DOWN_RATIO_THRESH = 0.8

hour_hist = {}
day_hist = {}
update_queue = queue.Queue()

def get_coin_list():
    URL = 'https://www.cryptocompare.com/api/data/coinlist/'

    logger.info('Get coin list from cryptocompare')
    rsp = requests.get(URL, timeout=10).json()
    coin_list = rsp['Data'].keys()
    return coin_list


def get_hist_data(period, fsym, tsym):
    URL_MIN = 'https://min-api.cryptocompare.com/data/histominute?fsym=%s&tsym=%s&limit=60' % (fsym, tsym)
    URL_HOUR = 'https://min-api.cryptocompare.com/data/histohour?fsym=%s&tsym=%s&limit=24' % (fsym, tsym)
    URL_DAY = 'https://min-api.cryptocompare.com/data/histoday?fsym=%s&tsym=%s&limit=1' % (fsym, tsym)
    if period == 'min':
        rsp = requests.get(URL_MIN, timeout=10).json()['Data']
    elif period == 'hour':
        rsp = requests.get(URL_HOUR, timeout=10).json()['Data']
    elif period == 'day':
        rsp = requests.get(URL_DAY, timeout=10).json()['Data']

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

#    daydata = day_hist.get(coin, None)
#    if daydata is None or daydata[-1]['time'] - now > 24*60*60:
#        logger.info('Update %s' % coin)
#        day_hist[coin] = get_hist_data('day', coin, 'BTC')
#        time.sleep(5)


    hourdata = hour_hist.get(coin, None)
    if hourdata is None or hourdata[-1]['time'] - now > 60*60:
        logger.info('Update %s' % coin)
        try:
            hour_hist[coin] = get_hist_data('hour', coin, 'BTC')
        except:
            time.sleep(5)
            return

        time.sleep(6)
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


def update_target_balance(coin_status, target_balance, coin):
    global hour_hist
    # get last hour price
    last_hour_vol = hour_hist[coin][-2]['volumeto']
    last_hour_price = hour_hist[coin][-2]['close']

    last_day_vol = np.sum([hour_hist[coin][x]['volumeto'] for x in range(1,24)])
    last_day_price = np.sum([hour_hist[coin][x]['close'] for x in range(1,24)]) / 23

    price_ratio = last_hour_price / last_day_price
    vol_ratio = last_hour_vol / (last_day_vol / 23.0)

    logger.info('%s last hour: %f %f,  last day: %f %f, price ratio = %.2f, vol ratio = %.2f' % (coin, last_hour_vol, last_hour_price, last_day_vol, last_day_price, price_ratio, vol_ratio))

    # Get currenct position
    if coin in coin_status:
        position = coin_status[coin]['Balance']
    else:
        position = 0

    # If no position and price and volome go up
    if position < 0.01 and price_ratio > PRICE_UP_MIN and price_ratio < PRICE_UP_MAX and vol_ratio > VOL_UP_THRESH and last_hour_vol > VOL_UP_THRESH:
        bid, ask = account.get_best_price('BTC-%s' % coin)
        midpt = (bid + ask) / 2
        position = POSITION_IN_BTC / midpt
        target_balance[coin] = position

        logger.info('Set position of %s = %f, price = %f' % (coin, position, midpt))


    # If have position and price and volome go down
    if position > 0.01 and price_ratio < PRICE_DOWN_THRESH and vol_ratio < VOL_DOWN_RATIO_THRESH:
        target_balance[coin] = 0
        logger.info('Set position of %s = 0' % coin)


def adjust_position(account, coin_status, target_balance):

    for coin in target_balance:
        if coin in coin_status:
            balance = coin_status[coin]['Balance']
        else:
            balance = 0

        if target_balance[coin] > 0.1 and balance < target_balance[coin] * 0.9:
            action = 'buy'
        elif target_balance[coin] < 0.1 and balance > 0:
            action = 'sell'
        else:
            continue

        pair = 'BTC-' + coin
        bid, ask = account.get_best_price(pair)
        price = (bid + ask) / 2

        # cancel all orders
        account.cancel_orders()

        if action == 'buy':
            qty = target_balance[coin] - balance
            account.buy(pair, qty, price)
        else:
            qty = balance
            account.sell(pair, qty, price)


def loop_execute():
    global account

    data = open('account.txt').readlines()
    key = data[0].strip()
    secret = data[1].strip()
    account = bittrex.Bittrex(key, secret)

    #account.buy('BTC-LTC', 0.1, 0.01)
    #account.cancel_orders()
    #adjust_position(account, {'LTC':{'Balance':0}}, {'LTC':0.2})

    # get balance
    coin_status = account.get_balances()
    logger.info(coin_status)
    target_balance = {}

    global update_queue

    while True:
        try:
            coin = update_queue.get_nowait()
        except:
            time.sleep(1)
            continue

        update_target_balance(coin_status, target_balance, coin)

        adjust_position(account, coin_status, target_balance)

        time.sleep(1)


if __name__ == '__main__':
    t = threading.Thread(target=loop_market)
    t.start()
    t = threading.Thread(target=loop_execute)
    t.start()

