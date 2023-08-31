import requests


class Bytecoin:
    def __init__(self, token):
        self.token = token
        url = 'https://coinbyte.ru/api/service/info'
        resp = requests.post(url, json={'access_token': token})
        #info = resp.json()
        raise Exception("Bytecoin is dead")
        if info['status'] == 'error':
            raise Exception(info['error'])
        else:
            self.name = info['data']['title']

    @staticmethod
    def get_coins(*users):
        coins = Bytecoin.users_info(*users, extended=True)
        coins = {i['id']: i['coins'] for i in coins}
        return coins

    def get_payment_url(self, amount=0.001, free_amount=False):
        url = 'https://vk.com/app7659711#' \
              'transfer_service={0}&sum={1}&fixed={2}'
        url = url.format(
            self.name,
            amount,
            0 if free_amount else 1
        )
        return url

    @staticmethod
    def create_payment_url(to, amount=0.001, free_amount=False):
        url = 'https://vk.com/app7659711#' \
              'transfer_user={0}&sum={1}&fixed={2}'
        url = url.format(
            to,
            amount,
            0 if free_amount else 1
        )
        return url

    def send_money(self, to_id, amount):
        url = 'https://coinbyte.ru/api/service/transfer'
        json = {
            'access_token': self.token,
            'user_id': to_id,
            'sum': amount
        }
        resp = requests.post(url, json=json).json()

        if resp['status'] == 'error':
            raise Exception(resp['error'])
        return resp['coins']

    def info(self):
        url = 'https://coinbyte.ru/api/service/info'
        resp = requests.post(url, json={
            'access_token': self.token
        }).json()

        return resp['data']

    def history(self, side=None, skip=0, user_id=None):
        url = 'https://coinbyte.ru/api/service/history'
        json = {'access_token': self.token}
        if side is not None:
            json['side'] = side
        if skip > 0:
            json['skip'] = skip
        if user_id is not None and side == 'to_user':
            json['user_id'] = user_id

        resp = requests.post(url, json=json).json()

        if resp['status'] == 'error':
            raise Exception(resp['error'])
        return resp['data']

    def statistics(self, date=None):
        url = 'https://coinbyte.ru/api/service/stat'
        json = {'access_token': self.token}
        if date is not None:
            json['date'] = date

        resp = requests.post(url, json=json).json()

        if resp['status'] == 'error':
            raise Exception(resp['error'])
        return resp['data']

    @staticmethod
    def users_info(*users, extended=False):
        url = 'https://coinbyte.ru/api/users/info'
        json = {
            'user_ids': users,
            'extended': 1 if extended else 0
        }
        resp = requests.post(url, json=json).json()

        if resp['status'] == 'error':
            raise Exception(resp['error'])
        return resp['users']
