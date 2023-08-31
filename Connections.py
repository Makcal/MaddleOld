import json
import os
from requests.exceptions import ConnectionError

import vk
import vkcoin
import Bytecoin
import coronacoin
import paperscrollsdk as ps_sdk
from vkpoint_api import VKPoint
from Catcoin import Catcoin
from Worldcoin import Worldcoin


with open(os.path.join(os.path.dirname(__file__), 'Account.txt')) as f:
    decoder = json.JSONDecoder()
    data = decoder.raw_decode(f.read())[0]
    ID = int(data['vk_id'])
    VK_TOKEN = data['vk_token']
    GROUP_TOKEN = data['group_token']
    BOT_SECRET = data['bot_secret']
    VKCOIN_KEY = data['vkcoin_key']
    BYTECOIN_TOKEN = data['bytecoin_token']
    PS_ID = data['ps_id']
    PS_TOKEN = data['ps_token']
    PS_SECRET = data['ps_secret']
    CORONA_TOKEN = data['corona_token']
    VKPOINT_TOKEN = data['vkpoint_token']
    CATCOIN_TOKEN = data['catcoin_token']
    WORLDCOIN_ID = data['worldcoin_id']
    WORLDCOIN_TOKEN = data['worldcoin_token']

vk_session = vk.Session(VK_TOKEN)
vk_api = vk.API(vk_session, v='5.122', lang='ru')

bot_session = vk.Session(GROUP_TOKEN)
bot_api = vk.API(bot_session, v='5.122', lang='ru')

vkcoin_api = vkcoin.VKCoin(ID, VKCOIN_KEY, VK_TOKEN)

try:
    bytecoin_api = Bytecoin.Bytecoin(BYTECOIN_TOKEN)
except Exception:
    print("Can't connect to bytecoin")
    bytecoin_api = None

ps_client = ps_sdk.PaperScroll(PS_ID, PS_TOKEN)
ps_api = ps_client.getApi()

coronacoin_api = coronacoin.CC(ID, CORONA_TOKEN)

vkpoint_api = VKPoint(ID, VKPOINT_TOKEN, 'https://maxmaddle.pasha1st.ru')

catcoin_api = Catcoin(ID, CATCOIN_TOKEN)

worldcoin_api = Worldcoin(WORLDCOIN_ID, WORLDCOIN_TOKEN)
