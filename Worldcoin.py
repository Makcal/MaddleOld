from random import randint

import requests


class Worldcoin:
    url = 'https://coin.world-coin-game.com/server/api.php'

    def __init__(self, shop_id, token):
        self.shop_id = shop_id
        self.token = token

    def _make_request(self, action, **kwargs):
        kwargs.update(
            action=action,
            group_id=self.shop_id,
            token=self.token
        )
        resp = requests.post(self.url, json=kwargs, timeout=1).json()
        if resp['status'] is False:
            raise Exception(resp['error'])
        else:
            return resp

    def make_link(self, amount, payload=None, free_amount=False):
        if payload is None:
            payload = randint(0, 9999999)
        return f'https://vk.com/app7614516#pay_{self.shop_id}_{amount}_' \
               f'{payload}' + ('_1' if not free_amount else '')

    def players_info(self, ids):
        return self._make_request('players',
                                  players=list(int(i) for i in ids))

    def history(self, filter_=0, count=1000, offset=0):
        return self._make_request('history', count=count, offset=offset,
                                  filter=filter_)['history']

    def send_money(self, to, amount, payload=None):
        if payload is None:
            payload = randint(0, 9999999)
        return self._make_request(
            'transaction',
            to=to,
            amount=amount,
            code=payload
        )

    def get_balance(self):
        return self._make_request('balance')

    # def set_callback(self, url=None):
    #     return self._make_request('set', callback=url)
