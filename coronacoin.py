import requests

class CC:
	def __init__(self, user_id, api_token):
		self.user_id = user_id
		self.api_token = api_token

	@staticmethod
	def create_link(id, amount, free_amount=False):
		return (f'https://vk.com/app7349811#merchant{id}_{int(amount)}' +
			('_1' if not free_amount else ''))

	def get_link(self, amount, free_amount=False):
		return (f'https://vk.com/app7349811#merchant{self.user_id}'
			    f'_{int(amount)}' + ('_1' if not free_amount else ''))

	def _call_method(self, method, **params):
		url = 'https://corona-coins.ru/api/'
		params['token'] = self.api_token
		params['method'] = method

		response = requests.post(url, json=params, timeout=5).json()
		if 'error' in response:
			raise Exception(response['error']['error_msg'])
		else:
			return response['response']

	def get_balances(self, *ids):
		return self._call_method('score', user_ids=ids)

	def send(self, to, amount):
		return self._call_method('transfer', to_id=to, amount=amount*1000)

	def history(self, type=1, offset=0):
		return self._call_method('history', type=type, offset=offset)
