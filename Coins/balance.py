import asyncio
from concurrent import futures

from Bytecoin import Bytecoin
from paperscrollsdk.exceptions import ApiError

from Connections import (vkcoin_api, ps_api, coronacoin_api, vkpoint_api,
                         catcoin_api, worldcoin_api)
from my_utils import try_coin


@try_coin('vkcoin')
def _get_vkcoins(*ids):
    ids = tuple(map(str, ids))
    resp = vkcoin_api.get_balance(*ids)

    for k in ids:
        if k not in resp:
            resp[k] = None
        elif resp[k] is not None:
            resp[k] /= 1000

    return ['vkcoin',
            {int(k): v for k, v in resp.items()}
            if len(ids) > 1 else resp[ids[0]]
            ]


@try_coin('bytecoin')
def _get_bytecoins(*ids):
    resp = Bytecoin.get_coins(*ids)

    for i in ids:
        if i not in resp:
            resp[i] = None

    return ['bytecoin', resp if len(ids) > 1 else resp[ids[0]]]


@try_coin('paperscroll')
def _get_paper(*ids):
    try:
        resp = ps_api.getUsersBalances(ids)
    except ApiError:
        return ['paperscroll',
                dict.fromkeys(ids, 'Повторите попытку')
                if len(ids) > 1 else None]

    data = {}

    for i in resp:
        data[i['user_id']] = i['balance'] / 1000

    for i in set(ids) - set(data):
        data[i] = None

    return ['paperscroll', data if len(ids) > 1 else data[ids[0]]]


@try_coin('coronacoin')
def _get_coronacoins(*ids):
    resp = coronacoin_api.get_balances(*ids)
    data = {}

    for i in resp:
        data[i['id']] = i['coins'] / 1000

    for i in set(ids) - set(data):
        data[i] = None

    return ['coronacoin', data if len(ids) > 1 else data[ids[0]]]


@try_coin('vkpoint')
def _get_vkpoints(*ids):
    resp = vkpoint_api.getApi().users.getTopIds(user_ids=ids)
    data = {}

    for u in resp.get('items', ()):
        data[int(u['user_id'])] = float(u['point'])

    for i in set(ids) - set(data):
        data[i] = None

    return ['vkpoint', data if len(ids) > 1 else data[ids[0]]]


@try_coin('catcoin')
def _get_catcoins(*ids):
    resp = catcoin_api.get_balances(ids)
    data = {}

    for u in resp:
        data[int(u)] = float(resp[u]) if type(resp[u]) != str else None

    for i in set(ids) - set(data):
        data[i] = None

    return ['catcoin', data if len(ids) > 1 else data[ids[0]]]


@try_coin('worldcoin')
def _get_worldcoins(*ids):
    resp = worldcoin_api.players_info(ids)
    data = {}

    for u in resp.get('players', ()):
        data[int(u)] = float(resp['players'][u]['coins'])

    for i in set(ids) - set(data):
        data[i] = None

    return ['worldcoin', data if len(ids) > 1 else data[ids[0]]]


_FUNCS = {'vkcoin': _get_vkcoins,
          'bytecoin': _get_bytecoins,
          'paperscroll': _get_paper,
          'coronacoin': _get_coronacoins,
          'vkpoint': _get_vkpoints,
          'catcoin': _get_catcoins,
          'worldcoin': _get_worldcoins}


def get_money(currs, *ids):
    if tuple(filter(lambda x: not isinstance(x, str), currs)) != ()\
            or tuple(filter(lambda x: not isinstance(x, int), ids)) != ():
        return None

    loop = asyncio.new_event_loop()
    executor = futures.ThreadPoolExecutor(max_workers=4)
    try:
        resp = [
            loop.run_in_executor(
                executor,
                _FUNCS[c],
                *ids
            ) for c in currs
        ]

    except KeyError:
        return None

    resp = asyncio.gather(*resp, loop=loop)
    resp = loop.run_until_complete(resp)
    return resp
