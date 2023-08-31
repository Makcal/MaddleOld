from Bytecoin import Bytecoin

from Connections import vkcoin_profile, ps_api, corona_profile


def _get_vkcoins(*ids):
    ids = tuple(map(str, ids))
    resp = vkcoin_profile.get_balance(*ids)

    for k in ids:
        if k not in resp:
            resp[k] = None
        elif resp[k] is not None:
            resp[k] /= 1000

    return {int(k): v for k, v in resp.items()} \
        if len(ids) > 1 else resp[ids[0]]


def _get_bytecoins(*ids):
    resp = Bytecoin.get_coins(*ids)

    for i in ids:
        if int(i) not in resp:
            resp[int(i)] = None

    return resp if len(ids) > 1 else resp[ids[0]]


def _get_paper(*ids):
    resp = ps_api.getUsersBalances(ids)
    data = {}

    for i in resp:
        data[i['user_id']] = i['balance'] / 1000

    for i in set(ids) - set(data):
        data[i] = None

    return data if len(ids) > 1 else data[ids[0]]


def _get_coronacoins(*ids):
    resp = corona_profile.get_balances(*ids)
    data = {}

    for i in resp:
        data[i['id']] = i['coins'] / 1000

    for i in set(ids) - set(data):
        data[i] = None

    return data if len(ids) > 1 else data[ids[0]]


_FUNCS = {'vkcoin': _get_vkcoins,
          'bytecoin': _get_bytecoins,
          'paperscroll': _get_paper,
          'coronacoin': _get_coronacoins}


def get_money(currs, *ids):
    if tuple(filter(lambda x: not isinstance(x, str), currs)) != ()\
            or tuple(filter(lambda x: not isinstance(x, int), ids)) != ():
        return None

    if len(currs) > 1:
        resp = []
        for c in currs:
            try:
                resp.append([c, _FUNCS[c](*ids)])
            except KeyError:
                resp.append([c, None])

        resp.sort(key=lambda x: x[1], reverse=True)

    else:
        try:
            resp = _FUNCS[currs[0]](*ids)
        except KeyError:
            resp = None

    return resp
