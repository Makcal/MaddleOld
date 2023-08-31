from .exceptions import NotImplementedError, ApiError
import requests
import base64


class PaperScrollClient:

    def __init__(self, access_token: str, merchant_id: int):
        if not access_token:
            raise AttributeError("Access token is not specified")

        if not merchant_id:
            raise AttributeError("Merchant ID is not specified")

        self.access_token = access_token
        self.merchant_id = merchant_id

        self.token = base64.b64encode("{}:{}".format(self.merchant_id, self.access_token).encode()).decode()
        self.api_url = "https://paper-scroll.ru/api/{}"

    def request(self, method: str, params: dict) -> dict:
        result = requests.post(
            self.api_url.format(method),
            json=params,
            headers={
                "Authorization": "Basic {}".format(self.token)
            },
            timeout=0.8
        ).json()

        if 'error' in result:
            raise ApiError(result['error']['error_code'],
                            result['error']['error_msg'],
                            result['error']['error_text'])

        return result['response']
