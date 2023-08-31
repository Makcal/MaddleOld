import re
import time
import asyncio
import aiohttp
from json import dumps

import pymysql

from Connections import *


DT_PATTERN = re.compile(r"(\d{4})-(\d\d)-(\d\d?)[A-Z](\d\d):(\d\d):(\d\d)")
NTF_MESSAGE = "Получен перевод от {name} на сумму {amount} {curr}"
SEND_METHODS = {
    "vkcoin": vkcoin_api.send_payment if vkcoin_api else lambda *args: None,
    "bytecoin": bytecoin_api.send_money if bytecoin_api else lambda *args: None,
    "paperscroll": ps_api.createTransfer if ps_api else lambda *args: None,
    "coronacoin": coronacoin_api.send if coronacoin_api else lambda *args: None,
    "vkpoint": vkpoint_api.merchantSend if vkpoint_api else lambda *args: None,
}


def get_db():
    try:
        return pymysql.connect(
            "192.168.7.3" if os.name == "posix" else "localhost",
            "maxim" if os.name == "posix" else "root",
            "12345" if os.name == "posix" else "12356790d",
            "vkwallet",
            cursorclass=pymysql.cursors.DictCursor
        )
    except pymysql.err.OperationalError:
        raise Exception("Can't connect to MySQL database!")


def set_service_name():
    try:
        vkcoin_api.set_shop_name("Maddle")
        catcoin_api.set_shop_name("Maddle")
    except Exception as e:
        print(f"Set_service_name - {e}")


def chunks(it, length):
    return (it[i:i+length] for i in range(0, len(it), length))


def time_dec(func):
    def wrapper(*args, **kwargs):
        t = time.time()
        resp = func(*args, **kwargs)
        print(func.__name__, "-", time.time() - t)
        return resp

    return wrapper

def try_coin(name):
    def dec(coin):
        def wrapper(*ids):
            try:
                return coin(*ids)
            except Exception as e:
                print(name.title(), "error -", e.__class__.__name__, e)
                return [
                    name,
                    dict.fromkeys(ids, "Приложение не работает.")
                    if len(ids) > 1
                    else "Приложение не работает."
                ]

        return wrapper
    return dec


async def _vk_users_fetch(api, session, users, **params):
    params.update(api._method_default_args) # noqa
    params["user_ids"] = ", ".join(map(str, users))
    params["access_token"] = api._session.access_token # noqa

    async with session.post("https://api.vk.com/method/users.get",
                            data=params) as response:
        return await response.json()


async def vk_users_info(api, users, **params):
    users = chunks(users, 1000)
    async with aiohttp.ClientSession() as session:
        tasks = [_vk_users_fetch(api, session, u, **params) for u in users]
        tasks = await asyncio.gather(*tasks)
        users = []
        for t in tasks:
            users.extend(t["response"])
        return users


def pprint(obj):
    print(dumps(obj, indent=4))


BOT_COMMANDS = ["О приложении", "Сообщить об ошибке"]
APP_DESCRIPTION = """В Maddle можно: 
смотреть свои балансы и курсы валют (зависят от активности переводов), 
переводить все валюты из одного места и добавлять комментарии, 
получать уведомления о входящих переводах,
смотреть историю переводов,
хранить валюту в банке;
а также множество возможностей ещё в разработке!"""
BUG_MESSAGE = "Опишите найденную ошибку. По желанию вы можете добавить " \
    "фото или видео"
TOO_SHORT_MESSAGE = "Слишком короткое сообщение. Напишите побольше"
