import requests, six, time

class VKPoint(object):

    _slots_ = ('_user_id', '_token', '_ApiUrl', '_AppUrl', '_UserAgent')

    def __init__(self, user_id, token, hosting):
        '''
        :param user_id: ID Вконтакте испольуемый для VKPoint
        :param token: Токен VKPoint
        :param hosting: http/https ссылка на хостинг, где установлен ваш сприпт
        '''
        self._user_id = user_id
        self._token = token
        self._ApiUrl = 'https://vkpoint.vposter.ru/api/method/'
        self._AppUrl = 'https://vk.com/app6748650'
        self._UserAgent = {
            "Accept-language": "en",
            "Cookie": "foo=bar",
            "User-Agent": "Mozilla/5.0 (iPad; U; CPU OS 3_2 like Mac OS X; en-us) AppleWebKit/531.21.10 (KHTML, like Gecko) Version/4.0.4 Mobile/7B334b Safari/531.21.102011-10-16 20:23:10",
            "Referer": hosting
            }

    @staticmethod
    def createLink(to, amount=None, free_amount=False):
        return 'https://vk.com/app6748650#u={}{}{}'.format(
            to,
            f'&point={amount}' if amount else '',
            '&fixed' if not free_amount else ''
        )

    def getLink(self, amount=None, free_amount=False):
        return 'https://vk.com/app6748650#u={}{}{}'.format(
            self._user_id,
            f'&point={amount}' if amount else '',
            '&fixed' if not free_amount else ''
        )

    def _sendRequests(self, method, params=None):
        response = requests.get(self._ApiUrl + method, params=params, headers=self._UserAgent).json()
        if 'error' in response:
            raise Exception(response)
        return response['response']

    def merchantGet(self, user_id):
        params = {
            'user_id_to': self._user_id,
            'user_id': user_id
        }
        return self._sendRequests('account.MerchantGet', params=params)

    def getPoint(self, user_id=None):
        user_id = user_id or self._user_id
        params = {
            'user_id': user_id,
        }
        return self._sendRequests('account.getPoint', params=params)

    def merchantSend(self, user_id, point):
        params = {
            'user_id_to': self._user_id,
            'user_id': user_id,
            'point': point,
            'access_token': self._token
        }
        return self._sendRequests('account.MerchantSend', params=params)

    def historyTransactions(self, user_id=None):
        params = {
            'user_id': user_id or self._user_id
        }
        return self._sendRequests('users.HistoryTransactions', params=params)

    def setCallback(self, url, id):
        params = {
            'access_token': self._token,
            'user_id': id,
            'callback': url
        }
        return self._sendRequests('account.changeSettings', params=params)

    def getApi(self):
        return VKPointApiMethod(self)


class VKPointApiMethod(object):

    __slots__ = ('_api', '_method', '_token', '_user_id')

    def __init__(self, vkPointObj, method=None):
        self._api = vkPointObj
        self._method = method
        self._token = vkPointObj._token
        self._user_id = vkPointObj._user_id

    def __getattr__(self, method):
        if '_' in method:
            m = method.split('_')
            method = m[0] + ''.join(i.title() for i in m[1:])

        return VKPointApiMethod(
            self._api,
            (self._method + '.' if self._method else '') + method
        )

    def __call__(self, **kwargs):
        for k, v in six.iteritems(kwargs):
            if isinstance(v, (list, tuple)):
                kwargs[k] = ','.join(str(x) for x in v)

        kwargs.update({
            'user_id_to': self._user_id,
            'user_id': kwargs.get('user_id', self._user_id),
            'access_token': self._token
        })

        return self._api._sendRequests(method=self._method, params=kwargs)


class VKPointPool(object):

    __slots__ = ('_api', '_LastTransactions')

    def __init__(self, ApiObject):
        self._api = ApiObject
        self._LastTransactions = self._api.historyTransactions()['items'][0]['id']

    def listen(self, sleep = 5):
        while True:
            history = self._api.historyTransactions()['items']
            if history[0] != self._LastTransactions:
                for payment in history:
                    if payment['id'] > self._LastTransactions:
                        yield payment
                else:
                    self._LastTransactions = self._api.historyTransactions()['items'][0]['id']

            time.sleep(sleep)
