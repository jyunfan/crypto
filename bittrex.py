import logging

import requests

from bittrex_api import bittrex

logger = logging.getLogger(__name__)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler = logging.FileHandler('crypto.log')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


class Bittrex():
    def __init__(self, key, secret):
        try:
            self.api = bittrex.Bittrex(key, secret)
        except:
            self.api = None


    def ready(self):
        return self.api is not None


    def get_balances(self):
        if self.api is None:
            return None

        rsp = self.api.get_balances()
        status = {}
        if rsp['success'] == True:
            for coin in rsp['result']:
                status[coin['Currency']] = coin
            return status
        else:
            return None


    def get_best_price(self, market):
        ''' market: e.g. BTC-LTC
        '''
        URL = 'https://bittrex.com/api/v1.1/public/getticker?market=%s' % market
        try:
            rsp = requests.get(URL, timeout=5).json()
            bid = rsp['result']['Bid']
            ask = rsp['result']['Ask']
            return bid, ask
        except:
            pass

    
    def cancel_orders(self):
        orders = self.api.get_open_orders()
        if orders['success'] != True:
            return

        orders = orders['result']
        logger.debug(orders)

        for order in orders:
            self.api.cancel(order['OrderUuid'])


    def buy(self, market, qty, price):
        self.api.buy_limit(market, qty, price)
        logger.debug('buy %s %f@%f' % (market, qty, price))


    def sell(self, market, qty, price):
        self.api.sell_limit(market, qty, price)
        logger.debug('sell %s %f@%f' % (market, qty, price))



