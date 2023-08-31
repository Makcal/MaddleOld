from random import randint

import requests


class Catcoin:
    url = 'https://likecoin2.ru/api/'

    def __init__(self, id, token):
        self.merchant_id = id
        self.token = token

    def _make_request(self, method, **kwargs):
        kwargs.update(
            method=method,
            merchantId=self.merchant_id,
            key=self.token
        )
        resp = requests.post(self.url, json=kwargs).json()
        if 'error' in resp:
            raise Exception(resp['error'])
        else:
            return resp['response']

    def make_link(self, amount, payload=None, free_amount=False):
        if payload is None:
            payload = randint(0, 99999999999)
        return f'https://vk.com/app7044895#x{self.merchant_id}_{amount}_' \
               f'{payload}' + ('_1' if free_amount else '')

    def get_balances(self, user_ids):
        return self._make_request('score',
                                  userIds=list(int(i) for i in user_ids))

    def history(self, tx, last_tx):
        return self._make_request('tx', tx=tx, lastTx=last_tx)

    def send_money(self, to, amount, mark_as_merchant=True):
        return self._make_request(
            'send',
            toId=to,
            amount=amount,
            markAsMerchant=mark_as_merchant
        )

    def set_callback(self, url=None):
        return self._make_request('set', callback=url)

    def set_shop_name(self, name):
        return self._make_request('setName', name=name)

    def missed_events(self):
        return self._make_request('lost')
