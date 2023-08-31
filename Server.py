import asyncio
import atexit
import datetime
import time
from hashlib import md5
from random import randint
from requests.exceptions import ConnectionError, ReadTimeout
from simplejson.errors import JSONDecodeError

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request, jsonify
from flask_cors import CORS
from paperscrollsdk.exceptions import ApiError
from pymysql import InternalError
from vk.exceptions import VkException
# from sqlalchemy import create_engine, text

from Coins import balance, remittance
from Connections import (ID, vk_api, bytecoin_api,
                         vkcoin_api, PS_SECRET, ps_api, coronacoin_api,
                         vkpoint_api, BOT_SECRET, bot_api, catcoin_api,
                         worldcoin_api)
from my_utils import (set_service_name, DT_PATTERN, chunks, NTF_MESSAGE,
                      get_db, vk_users_info, pprint, SEND_METHODS,
                      BOT_COMMANDS, APP_DESCRIPTION, BUG_MESSAGE,
                      TOO_SHORT_MESSAGE)

app = Flask(__name__)
cors = CORS(app, origins=[
    r'https://.*\.ngrok\.io',
    r'https://.*-app7493327-.*\.pages\.vk-apps\.com',
    r'https://.*\.loca\.lt',
    r'https://vk-wallet-frontend\.now\.sh',
    r'https://vk-wallet-frontend\.vercel\.app',
    r'https://app\.paper-scroll\.ru',
])
app.config['CORS_HEADERS'] = 'Content-Type'

# engine = ...

with get_db() as curs:
    curs.execute('select `name` from currencies')
    CURRENCIES = {i['name'] for i in curs.fetchall()}
    # CURRENCIES.remove('worldcoin')
    # CURRENCIES.remove('catcoin')

    curs.execute('select * from ntfs_settings')
    curs.fetchall()
    NTFS_SETTINGS = {i[0] for i in curs.description} - {'userId'}

    curs.execute('select * from general_settings')
    curs.fetchall()
    GENERAL_SETTINGS = {i[0] for i in curs.description} - {'userId'}
del curs

SETTINGS_TYPES = {'ntfs', 'general'}
SETTINGS_KEYS = {
    'ntfs': NTFS_SETTINGS,
    'general': GENERAL_SETTINGS
}

@app.route('/get', methods=['POST'])
def get_data():
    """
    Satisfactory structure.
    json = {
        "int"

        id: n
    }
    """
    try:
        json: dict = request.json
        if json is None or 'id' not in json.keys():
            return jsonify({'data': {}, 'code': 1}), 400

        id_ = json['id']
        if not isinstance(id_, int):
            return jsonify({'data': {}, 'code': 2}), 400
        if id_ < 1 or id_ > 2147483647:
            return jsonify({'data': {}, 'code': 6}), 400

        with get_db() as cur:
            new = False
            cur.execute(f'select new_transactions from users where id = {id_}')
            res = cur.fetchall()
            if not res:
                new = True
                res = ({'new_transactions': 0},)
                cur.execute(f'call add_user({id_})')

            cur.execute('select name, price, yest_price from currencies')
            rates = {c['name']: (c['price'], c['price'] - c['yest_price'])
                     for c in cur.fetchall()}

        user = balance.get_money(CURRENCIES, id_)
        user.sort(key=lambda c: c[1] if isinstance(c[1], (int, float)) else 0,
                  reverse=True)

        for c in user:
            c.extend(rates[c[0]])

        return jsonify({'data': user,
                        'new_trans': res[0]['new_transactions'],
                        'new_user': new,
                        'code': 0}), 200

    except Exception as e:
        # raise e
        print('Get - ', e.__class__.__name__, e)
        pprint(request.json)
        return jsonify({'data': {}, 'code': -1}), 500


@app.route('/save_settings', methods=['POST'])
def save_settings():
    """
    Satisfactory structure. Be very careful when make this request!
    json = {
        "int"

        id: val,

        ntfs: {
            "bool"

            transactions: value,
            market_news: value,
            requests: value,
            mailing: value
        }
        "or"

        general: {
            "bool"

            reset_filters: value,
            confirmation: value,
        }

        "other settings are possible in the future"
    }
    """
    try:
        json: dict = request.json
        if json is None or \
                'id' not in json.keys() or \
                not SETTINGS_TYPES & json.keys():
            return jsonify({'code': 1}), 400

        id_ = json['id']
        settings_type = tuple(SETTINGS_TYPES & json.keys())[0]

        if not (isinstance(id_, int) and
                isinstance(json[settings_type], dict)):
            return jsonify({'code': 2}), 400

        if SETTINGS_KEYS[settings_type] - json[settings_type].keys():
            return jsonify({'code': 3}), 400

        settings: dict = json[settings_type]
        for k, v in settings.items():
            settings[k] = str(v).replace('"', r'\"')
        settings_items = ', '.join(f'{k} = "{v}"' for k, v in settings.items())

        with get_db() as cur:
            if settings_type == 'ntfs':
                table = 'ntfs_settings'
            elif settings_type == 'general':
                table = 'general_settings'

            try:
                cur.execute(f'update {table} '
                            f'set {settings_items} '
                            f'where userId = {id_}')
            except InternalError:
                return jsonify({'code': 4}), 400

        return jsonify({'code': 0}), 200

    except Exception as e:
        print('Settings - ', e.__class__.__name__, e)
        pprint(request.json)
        return jsonify({'code': -1}), 500


@app.route('/settings', methods=['POST'])
def get_settings():
    """
    Satisfactory structure.
    json = {
        "int"

        id: n
    }
    """
    try:
        json: dict = request.json
        if json is None or 'id' not in json.keys():
            return jsonify({'data': {}, 'code': 1}), 400

        id_ = json['id']
        if not isinstance(id_, int):
            return jsonify({'data': {}, 'code': 2}), 400
        if id_ < 1 or id_ > 2147483647:
            return jsonify({'data': {}, 'code': 6}), 400

        with get_db() as cur:
            data = {}

            cur.execute(f'select {", ".join(NTFS_SETTINGS)} '
                        'from ntfs_settings '
                        f'where userId = {id_}')
            ntfs = cur.fetchall()
            if not ntfs:
                return jsonify({'data': {}, 'code': 5}), 400

            cur.execute(f'select {", ".join(GENERAL_SETTINGS)} '
                        'from general_settings '
                        f'where userId = {id_}')
            general = cur.fetchall()

            data['ntfs'] = ntfs[0]
            data['general'] = general[0]

        return jsonify({'data': data, 'code': 0})

    except Exception as e:
        print('Settings - ', e.__class__.__name__, e)
        pprint(request.json)
        return jsonify({'data': {}, 'code': -1}), 500


'''@app.route('/delete', methods=['POST'])
def delete_user():
    json: dict = request.json
    with get_db() as cur:
        id_ = str(json['id']).join(["\"", "\""])

        if cur.execute(f'delete from users where id = {id_}') == 0:
            return jsonify({'code': 1}), 400
        else:
            return jsonify({'code': 0}), 200'''


'''@app.route('/remittance', methods=['POST'])
def transaction():
    """
    Satisfactory structure. Be very careful when make this request!
    json = {
        "int"
        from: id1,
        to: id2,

        "float/double/int"
        amount: n,

        "str"
        currency: type
    }
    """
    try:
        json: dict = request.json
        if json is None or \
                {'from', 'to', 'amount', 'currency'} - json.keys() != set():
            return jsonify({'code': 1, 'url': ''}), 400

        from_ = json['from']
        to = json['to']
        amount = json['amount']
        curr = json['currency']
        if not (isinstance(from_, int) and
                isinstance(to, int) and
                isinstance(amount, (float, int)) and
                isinstance(curr, str)):
            return jsonify({'code': 2, 'url': ''}), 400

        if amount <= 0 or to <= 0:
            return jsonify({'code': 6, 'url': ''}), 400

        if from_ == to:
            return jsonify({'code': 7, 'url': ''}), 400

        if curr not in CURRENCIES:
            return jsonify({'code': 3, 'url': ''}), 400

        rem = getattr(remittance_simple, curr + '_rem')
        res = rem(to, amount)

        if res != '':
            return jsonify({'code': 0, 'url': res}), 200
        else:
            return jsonify({'code': 7, 'url': ''}), 400

    except Exception:
        return jsonify({'code': -1, 'url': ''}), 500'''


@app.route('/remittance', methods=['POST'])
def smart_transaction():
    """
    Satisfactory structure. Be very careful when make this request!
    json = {
        "int"
        from: id1,
        to: id2,

        "float/double/int"
        amount: n,

        "str"
        currency: type,

        message: text
    }
    """
    try:
        json: dict = request.json
        if json is None or \
                {'from', 'to', 'amount', 'currency', 'message'} - \
                json.keys() != set():
            return jsonify({'code': 1, 'url': ''}), 400

        from_ = json['from']
        to = json['to']
        amount = json['amount']
        curr = json['currency']
        msg = json['message']

        if not (isinstance(from_, int) and
                isinstance(to, (int, str)) and
                isinstance(amount, (float, int)) and
                isinstance(curr, str) and
                isinstance(msg, str)):
            return jsonify({'code': 2, 'url': ''}), 400

        if (isinstance(to, int) and to < 1) or amount <= 0 or from_ < 1:
            return jsonify({'code': 6, 'url': ''}), 400

        if from_ == to:
            return jsonify({'code': 7, 'url': ''}), 400

        if curr not in CURRENCIES:
            return jsonify({'code': 8, 'url': ''}), 400

        if len(msg) > 255:
            return jsonify({'code': 9, 'url': ''}), 400

        if isinstance(to, str):
            to = vk_api.utils.resolveScreenName(screen_name=to)
            if to['type'] != 'user':
                return jsonify({'code': 11, 'url': ''}), 400
            else:
                to = to['object_id']
                if from_ == to:
                    return jsonify({'code': 7, 'url': ''}), 400

        rem = getattr(remittance, curr + '_rem')
        url = rem(amount)

        if url:
            with get_db() as cur:
                if not cur.execute(
                    'update users set '
                    '{0}_to = {1}, {0}_time = {3}, {0}_msg = "{4}"'
                    'where id = {2}'.format(
                        curr,
                        to,
                        from_,
                        time.time(),
                        msg.replace('"', r'\"')
                    )
                ):
                    return jsonify({'code': 5, 'url': ''}), 400

            return jsonify({'code': 0, 'url': url}), 200
        else:
            return jsonify({'code': 10, 'url': ''}), 400

    except Exception as e:
        print('Transactions - ', e.__class__.__name__, e)
        pprint(request.json)
        return jsonify({'code': -1, 'url': ''}), 500


@app.route('/friends', methods=['POST'])
def get_friends():
    """
    Satisfactory structure.
    json = {
        "int"
        id: n,

        "str"
        currency: name
    }
    """
    try:
        json: dict = request.json
        if json is None or {'id', 'currency'} - json.keys() != set():
            return jsonify({'data': [], 'code': 1}), 400

        id_ = json['id']
        curr = json['currency']
        if not (isinstance(id_, int) and isinstance(curr, str)):
            return jsonify({'data': [], 'code': 2}), 400

        if curr not in CURRENCIES:
            return jsonify({'data': [], 'code': 3}), 400

        if id_ < 1:
            return jsonify({'data': [], 'code': 3}), 400

        try:
            friends = vk_api.friends.get(
                user_id=id_,
                fields='photo_200'
            )['items']
        except VkException:
            return jsonify({'data': [], 'code': 7}), 400

        for i in range(len(friends)-1, -1, -1):
            if 'deactivated' in friends[i]:
                friends.pop(i)

        data = []
        ids = [i['id'] for i in friends]

        money = {}
        for i in list(chunks(ids, 100)):
            money.update(balance.get_money((curr,), *i)[0][1])

        def select(user):
            resp = {}
            for p in ('id',
                      'first_name',
                      'last_name',
                      'photo_200'):
                resp[p] = user[p]
            resp['money'] = money[user['id']]
            return resp

        for f in friends:
            data.append(select(f))

        data.sort(
            key=lambda x: (0 if isinstance(x['money'], (str, type(None)))
                           else -x['money'],
                           x['first_name'])
        )
        return jsonify({'data': data, 'code': 0}), 200

    except Exception as e:
        print('Friends - ', e.__class__.__name__, e)
        pprint(request.json)
        return jsonify({'data': [], 'code': -1}), 500


@app.route('/history', methods=['POST'])
def history():
    """
    Satisfactory structure.
    json = {
        "int"

        id: n,

        [optional] size = 20,
        [optional] skip = 0,

        "str"

        [optional] currency: name
    }
    """
    try:
        json: dict = request.json
        if json is None or 'id' not in json.keys():
            return jsonify({'transactions': [], 'users': {}, 'code': 1}), 400

        id_ = json['id']
        if not isinstance(id_, int):
            return jsonify({'transactions': [], 'users': {}, 'code': 2}), 400

        if 'currency' in json and json['currency'] in CURRENCIES:
            curr = json['currency']
        else:
            curr = None

        if 'size' in json and isinstance(json['size'], int):
            size = json['size']
        else:
            size = 20

        if 'skip' in json and isinstance(json['skip'], int):
            skip = json['skip']
        else:
            skip = 0

        with get_db() as cur:
            cur.execute('update users set new_transactions = 0 '
                        f'where id = {id_}')
            cur.execute(
                'select * from transactions '
                'where (`from` = {0} or `to` = {0}){1} '
                'order by time desc limit {2}, {3}'.format(
                    id_,
                    f' and currency = "{curr}"' if curr is not None else '',
                    skip,
                    size
                )
            )
            data = cur.fetchall()
            if data == ():
                return (jsonify({'transactions': [], 'users': {}, 'code': 0}),
                        200)

            ids = set()
            for i in data:
                i['amount'] = float(i['amount'])
                ids.update({i['from'], i['to']})
            ids = ids - {0, id_}

            users_raw = asyncio.run(vk_users_info(
                vk_api,
                tuple(ids),
                fields='photo_200'
            ))
            users = {}

            for u in users_raw:
                user = {}
                for p in ('first_name', 'last_name', 'photo_200'):
                    user[p] = u[p]
                users[u['id']] = user

            return (
                jsonify({'transactions': data, 'users': users, 'code': 0}),
                200
            )

    except Exception as e:
        print('History - ', e.__class__.__name__, e)
        pprint(request.json)
        return jsonify({'transactions': [], 'users': {}, 'code': -1}), 500


@app.route('/favourites', methods=['POST'])
def get_favourites():
    """
    Satisfactory structure.
    json = {
        "int"

        id: n
    }
    """
    try:
        json: dict = request.json
        if json is None or 'id' not in json.keys():
            return jsonify({'favourites': [], 'code': 1}), 400

        id_ = json['id']
        if not isinstance(id_, int):
            return jsonify({'favourites': [], 'code': 2}), 400

        with get_db() as cur:
            cur.execute('select id from users '
                        f'where id = {id_}')
            if not cur.fetchall():
                return jsonify({'favourites': [], 'code': 5}), 400

            cur.execute('select favourite from favourites '
                        f'where userId = {id_}')
            favs = asyncio.run(vk_users_info(
                vk_api,
                [f['favourite'] for f in cur.fetchall()],
                fields='photo_200'
            ))

            for i in range(len(favs)):
                user = {}
                for p in ('id', 'first_name', 'last_name', 'photo_200'):
                    user[p] = favs[i][p]
                favs[i] = user

            return jsonify({'favourites': favs, 'code': 0})

    except Exception as e:
        print('Favourites - ', e.__class__.__name__, e)
        pprint(request.json)
        return jsonify({'favourites': {}, 'code': -1}), 500


@app.route('/save_favourites', methods=['POST'])
def save_favourites():
    """
    Satisfactory structure.
    json = {
        "int"

        id: n

        "list/array"

        favourites: list
    }
    """
    try:
        json: dict = request.json
        if json is None or {'id', 'favourites'} - json.keys():
            return jsonify({'code': 1}), 400

        id_ = json['id']
        new_favs = json['favourites']
        if not (isinstance(id_, int) and isinstance(new_favs, list)):
            return jsonify({'code': 2}), 400

        if tuple(filter(lambda f: not isinstance(f, int), new_favs)):
            return jsonify({'code': 4}), 400

        if len(new_favs) not in range(1, 11):
            return jsonify({'code': 6}), 400

        with get_db() as cur:
            cur.execute(f'select id from users where id = {id_}')
            if not cur.fetchall():
                return jsonify({'code': 5}), 400

            cur.execute('delete from favourites '
                        f'where userId = {id_}')

            seen = set()
            remove = []
            for i in range(len(new_favs)):
                if new_favs[i] in seen or new_favs[i] == id_:
                    remove.append(i)
                else:
                    seen.add(new_favs[i])
            for i in reversed(remove):
                new_favs.pop(i)

            for fav in new_favs:
                cur.execute('insert favourites (userId, favourite) '
                            f'values ({id_}, {fav})')

            return jsonify({'code': 0})

    except Exception as e:
        print('Save favourites - ', e.__class__.__name__, e)
        pprint(request.json)
        return jsonify({'code': -1}), 500


@app.route('/bank', methods=['POST'])
def bank():
    """
    Satisfactory structure.
    json = {
        "int"

        id: n,
        amount: money (negative means withdrawing,
            positive means replenishment, zero means get balance)

        "str"

        currency: name
    }
    """
    try:
        json: dict = request.json
        if json is None or {'id', 'amount', 'currency'} - json.keys():
            return jsonify({'data': '', 'code': 1}), 400

        id_ = json['id']
        amount = json['amount']
        curr = json['currency']
        if not (isinstance(id_, int) and
                isinstance(amount, int) and
                isinstance(curr, str)):
            return jsonify({'data': '', 'code': 2}), 400

        if curr not in CURRENCIES:
            return jsonify({'data': '', 'code': 6}), 400

        if amount <= 0:
            with get_db() as cur:
                cur.execute(f'select id from users where id = {id_}')
                if not cur.fetchall():
                    return jsonify({'data': 0, 'code': 5})

                cur.execute(f'select {curr} from bank where userId = {id_}')
                money = cur.fetchall()
                if not money:
                    return jsonify({'data': 0, 'code': 7} if amount != 0
                                   else {'data': 0, 'code': 0})
                else:
                    if amount == 0:
                        return jsonify({'data': money[0][curr], 'code': 0})
                    else:
                        if money[0][curr] == 0:
                            return jsonify({'data': 0, 'code': 7})
                        else:
                            method = SEND_METHODS.get(curr, None)
                            if method is None:
                                return jsonify({'data': '', 'code': 6})

                            amount = min(-amount, money[0][curr])

                            method(id_, amount)
                            cur.execute('update bank set '
                                        f'{curr} = {curr} - '
                                        f'{amount} '
                                        f'where userId = {id_}')
                            cur.execute('insert transactions (`from`, `to`, '
                                        '`time`, currency, amount, message) '
                                        f'values ({id_}, 0, {time.time()}, '
                                        f'"{curr}", -{amount}, "")')
                            print(f'User {id_} has withdrawn '
                                  f'{amount} {curr}s')

                            return jsonify({
                                'data': amount,
                                'code': 0
                            })

        else:
            rem = getattr(remittance, curr + '_rem')
            url = rem(amount)

            if url:
                with get_db() as cur:
                    if not cur.execute(
                        'update users set '
                        '{0}_to = 0, {0}_time = {2}, {0}_msg = "" '
                        'where id = {1}'.format(
                            curr,
                            id_,
                            time.time()
                        )
                    ):
                        return jsonify({'data': '', 'code': 5}), 400

                return jsonify({'data': url, 'code': 0})
            else:
                return jsonify({'data': '', 'code': 8}), 400

    except Exception as e:
        print('Bank - ', e.__class__.__name__, e)
        pprint(request.json)
        return jsonify({'url': '', 'code': -1}), 500


@app.route('/bot', methods=['POST'])
def bot():
    json: dict = request.json
    # pprint(json)
    if json is None or \
            'secret' not in json.keys() or \
            json['secret'] != BOT_SECRET:
        print('Fake request on bot`s callback.')  # hacking attempt
        return 'ok'

    if json['type'] == 'confirmation':  # подтверждение сервера
        return '8849b943'
    elif json['type'] != 'message_new':  # собатие не поддерживается
        return 'ok'

    json = json['object']
    user_id = json['message']['from_id']

    if json['message'].get('payload') == '{"command":"start"}' or \
            json['message']['conversation_message_id'] == 1:  # первое общение
        bot_api.messages.send(
            user_id=user_id,
            message='Привет! Вот список доступных команд:\n' +
                    '\n'.join(
                        f'{i+1}) {BOT_COMMANDS[i]}'
                        for i in range(len(BOT_COMMANDS))
                    ),
            keyboard={
                'one_time': True,
                'buttons': [[
                    {  # первая строчка, одна кнопка
                        'action': {
                            'type': 'open_app',
                            'app_id': 7493327,
                            'label': 'Открыть приложение',
                        }
                    }
                ]] + [
                    [  # по команде на строчку
                        {
                            'color': 'primary',
                            'action': {
                                'type': 'text',
                                'label': command
                            }
                        }
                    ] for command in BOT_COMMANDS
                ]
            },
            random_id=randint(-2147483648, 2147483647)
        )
        return 'ok'
    else:
        try:
            last_message = bot_api.messages.getHistory(
                offset=1, count=1,  # последнее сообщение бота
                user_id=user_id,
                start_message_id=json['message']['id']
            )['items'][0]
        except IndexError:
            return 'ok'

    if json['message']['text'].lower().strip() in \
            ('сообщить об ошибке', 'сообщить о ошибке', 'сообщить о баге'):
        # реакция на "сообщить об ошибке"
        bot_api.messages.send(
            user_id=user_id,
            message=BUG_MESSAGE,
            payload='{"command":"bug"}',
            random_id=randint(-2147483648, 2147483647)
        )

    elif json['message']['text'].lower().strip() in \
            ('о приложении', 'об приложении', 'описание'):
        # реакция на "о приложении"
        bot_api.messages.send(
            user_id=user_id,
            message=APP_DESCRIPTION,
            keyboard={
                'one_time': True,
                'buttons': [[
                    {  # первая строчка, одна кнопка
                        'action': {
                            'type': 'open_app',
                            'app_id': 7493327,
                            'label': 'Открыть приложение',
                        }
                    }
                ]] + [
                    [  # по команде на строчку
                        {
                            'color': 'primary',
                            'action': {
                                'type': 'text',
                                'label': command
                            }
                        }
                    ] for command in BOT_COMMANDS
                ]
            },
            random_id=randint(-2147483648, 2147483647)
        )

    elif last_message['out'] == 1 and \
            last_message.get('payload') == '{"command":"bug"}':
        if len(json['message']['text'].strip()) < 10:
            bot_api.messages.send(
                user_id=user_id,
                message=TOO_SHORT_MESSAGE,
                payload='{"command":"bug"}',
                random_id=randint(-2147483648, 2147483647)
            )
            return 'ok'

        with get_db() as cur:
            message = json['message']['text'].replace('"', r'\"')
            try:
                cur.execute('insert bug_reports (`from`, `description`) '
                            f'values ({user_id}, "{message}")')
            except Exception as e:
                print(e)
                return 'ok'

            attachments = tuple(
                (a['photo']['sizes'][-1]['url'],)
                for a in json['message']['attachments']
                if a['type'] == 'photo'
            )
            cur.executemany('insert bug_attachments (report_id, link) '
                            'values (last_insert_id(), %s)',
                            attachments)

        bot_api.messages.send(
            user_id=user_id,
            message='Сообщение об ошибке успешно отправлено',
            keyboard={
                'one_time': True,
                'buttons': [[
                    {  # первая строчка, одна кнопка
                        'action': {
                            'type': 'open_app',
                            'app_id': 7493327,
                            'label': 'Открыть приложение',
                        }
                    }
                ]] + [
                               [  # по команде на строчку
                                   {
                                       'color': 'primary',
                                       'action': {
                                           'type': 'text',
                                           'label': command
                                       }
                                   }
                               ] for command in BOT_COMMANDS
                           ]
            },
            random_id=randint(-2147483648, 2147483647)
        )
        bot_api.messages.send(
            user_id=ID,
            message=f'Новое сообщение об ошибке от @id{user_id} '
                    f'(id{user_id}):\n' + message,
            random_id=randint(-2147483648, 2147483647)
        )

    else:
        bot_api.messages.send(
            user_id=user_id,
            message='Не понимаю о чём вы. Список доступных команд:\n' +
                    '\n'.join(
                        f'{i+1}) {BOT_COMMANDS[i]}'
                        for i in range(len(BOT_COMMANDS))
                    ),
            keyboard={'one_time': True,
                      'buttons': [[{
                          'action': {
                              'type': 'open_app',
                              'app_id': 7493327,
                              'label': 'Открыть приложение',
                          }
                      }]] +
                      [
                          [
                               {'color': 'primary',
                                'action': {
                                   'type': 'text',
                                   'label': command
                                }}
                          ]
                          for command in BOT_COMMANDS
                      ]},
            random_id=randint(-2147483648, 2147483647)
        )

    return 'ok'


@app.route('/vkcoin', methods=['POST'])
def vkcoin():
    """
    {
        id: 2627951,
        amount: 1,
        payload: 1234,
        created_at: 1555612247,
        from_id: 19039187,
        to_id: 360092594,
        key: '5bb8fcefd43242773e34eb485f377463'

        <id;from_id;amount;payload;merchantKey> - md5
    }
    """
    try:
        json: dict = request.json
        if json is None:
            return 'OK'

        try:
            hash_ = '{id};{from_id};{amount};{payload};{key_}'.format(
                        **json,
                        key_=vkcoin_api.key
                    )
            if md5(bytes(hash_, 'utf-8')).hexdigest() != json['key']:
                return 'OK'

        except KeyError:
            return 'OK'

        user_id = json['from_id']
        json['amount'] /= 1000
        amount = json['amount']

        with get_db() as cur:
            cur.execute('select vkcoin_to, vkcoin_time, vkcoin_msg '
                        f'from users where id = {user_id}')
            rem = cur.fetchall()

            if rem and rem[0]['vkcoin_to'] is not None:
                cur.execute('update users set '
                            'vkcoin_to = null, '
                            'vkcoin_time = null, '
                            'vkcoin_msg = null '
                            f'where id = {user_id}'
                            )

                to = rem[0]['vkcoin_to']
                time_ = rem[0]['vkcoin_time']
                msg = rem[0]['vkcoin_msg'].replace('"', r'\"')

                if json['created_at'] - time_ > 900:
                    print(
                        'Remittance expired! Time passed: {}'
                        '\n\tRemittance - {}. Returned {} vkcoins'
                        ''.format(json['created_at'] - time_, rem, amount)
                    )

                    vkcoin_api.send_payment(user_id, amount)
                    return 'OK'

                if to == 0:
                    if not cur.execute('update `bank` set '
                                       f'vkcoin = vkcoin + {amount} '
                                       f'where userId = {user_id}'):
                        cur.execute('insert `bank` (userId, vkcoin) '
                                    f'values ({user_id}, {amount})')

                    cur.execute('insert transactions (`from`, `to`, `time`, '
                                'currency, amount, message) values '
                                '({from_id}, 0, {created_at}, '
                                '"vkcoin", {amount}, "")'
                                ''.format(**json)
                                )
                    print(f'User {user_id} has replenished his account '
                          f'for {amount} vkcoins.')
                    return 'OK'

                try:
                    vkcoin_api.send_payment(to, amount)
                except Exception as e:
                    if 'BAD_ARG' in str(e):
                        print(f'{time.ctime()} - Fail.\n'
                              f'\tCan`t send to id{to}! '
                              f'Returned {amount} vkcoins.')

                    vkcoin_api.send_payment(user_id, amount)

                else:
                    cur.execute('insert transactions (`from`, `to`, `time`, '
                                'currency, amount, message) values '
                                '({from_id}, {to}, {created_at}, '
                                '"vkcoin", {amount}, "{msg}")'
                                ''.format(**json, to=to, msg=msg)
                                )
                    cur.execute('update currencies '
                                'set today_trans = today_trans + '
                                f'{amount} '
                                f'where `name` = "vkcoin"')

                    cur.execute('select new_transactions from users '
                                f'where id = {to}')
                    news = cur.fetchall()
                    if news and news[0]['new_transactions'] < 255:
                        cur.execute('update users set new_transactions = '
                                    f'new_transactions + 1 where id = {to}')

                    cur.execute('select transactions from ntfs_settings '
                                f'where userId = {to}')
                    tr_enabled = cur.fetchall()
                    tr_enabled = bool(tr_enabled[0]['transactions']) \
                        if tr_enabled else False

                    if vk_api.apps.isNotificationsAllowed(user_id=to)[
                            'is_allowed'] and tr_enabled:
                        user = vk_api.users.get(user_ids=[user_id],
                                                name_case='gen')[0]
                        name = ' '.join(
                            (user['first_name'], user['last_name'])
                        )
                        vk_api.notifications.sendMessage(
                            user_ids=[to],
                            message=NTF_MESSAGE.format(name=name,
                                                       amount=amount,
                                                       curr='VK Coin`ов'),
                        )

                    print(f'{time.ctime()} - Success!\n'
                          f'\t{amount} vkcoins '
                          f'from id{user_id} to id{to}')

                finally:
                    return 'OK'

            else:
                vkcoin_api.send_payment(user_id, amount)

                rem = {'from': user_id, 'to': rem[0]['vkcoin_to']}
                print(f'{time.ctime()} - User or target not found!\n'
                      f'\tReturned {amount} vkcoins. Remittance - {rem}')
                return 'OK'

    except Exception as e:
        print('Vkcoin - ', e.__class__.__name__, e)
        pprint(request.json)
        return 'OK'


@app.route('/bytecoin', methods=['POST'])
def bytecoin():
    """
    {
        event: 'transfer',
        data: {
            user_id: 205580268,
            service_id: '5d3cf1c2774d4315b39d13ba',
            side: 'to_service',
            sum: 666,
            created_at: '2019-07-28T03:00:02.082Z',
            created_at_text: 'Сегодня, в 6:00'
        }
    }
    """
    try:
        json: dict = request.json
        if json is None or json['event'] != 'transfer' or \
                {'user_id', 'service_id', 'side',
                 'sum', 'created_at', 'created_at_text'} != \
                set(json['data'].keys()):
            return 'ok'

        json = json['data']
        user_id = json['user_id']
        amount = round(json['sum'], 3)
        created_at = DT_PATTERN.findall(json['created_at'])[0]
        created_at = tuple(map(int, created_at))
        # noinspection PyTypeChecker
        created_at = time.mktime(created_at + (0, 0, 0))
        json['created_at'] = created_at

        with get_db() as cur:
            cur.execute('select bytecoin_to, bytecoin_time, bytecoin_msg '
                        f'from users where id = {user_id}')
            rem = cur.fetchall()

            if rem != () and rem[0]['bytecoin_to'] is not None:
                cur.execute(f'update users set '
                            f'bytecoin_to = null, '
                            f'bytecoin_time = null, '
                            f'bytecoin_msg = null '
                            f'where id = {user_id}')

                to = rem[0]['bytecoin_to']
                time_ = rem[0]['bytecoin_time']
                msg = rem[0]['bytecoin_msg'].replace('"', r'\"')

                if created_at - time_ > 900:
                    print('Remittance expired! Time passed: {}'
                          '\n\tRemittance - {}. Returned {} bytecoins'
                          ''.format(
                                created_at - time_,
                                rem,
                                amount
                            ))

                    bytecoin_api.send_money(user_id, amount)
                    return 'ok'

                if to == 0:
                    if not cur.execute('update `bank` set '
                                       f'bytecoin = bytecoin + {amount} '
                                       f'where userId = {user_id}'):
                        cur.execute('insert `bank` (userId, bytecoin) '
                                    f'values ({user_id}, {amount})')

                    cur.execute('insert transactions (from, to, time, '
                                'currency, amount, message) values '
                                '({user_id}, 0, {created_at}, '
                                '"bytecoin", {sum}, "")'
                                ''.format(**json)
                                )
                    print(f'User {user_id} has replenished his account '
                          f'for {amount} bytecoins.')
                    return 'OK'

                try:
                    # print(1)
                    bytecoin_api.send_money(to, amount)
                    # print(2)
                except Exception as e:
                    print('Bytecoin', e.__class__.__name__, e)
                    if 'ERROR' in str(e):
                        print(f'{time.ctime()} - Fail.\n'
                              f'\tCan`t send to id{to}! '
                              f'Returned {amount} bytecoins.')
                    if 'BAD_ARGS' in str(e):
                        print(f'{time.ctime()} - Fail.\n'
                              f'\tBad request! Request: '
                              f'{amount} -> {to}. Returned')

                    bytecoin_api.send_money(user_id, amount)

                else:
                    cur.execute('insert transactions (from, to, time, '
                                'currency, amount, message) values '
                                '({user_id}, {to}, {created_at}, '
                                '"bytecoin", {sum}, "{msg}")'
                                ''.format(**json, to=to, msg=msg)
                                )
                    cur.execute('update currencies '
                                f'set today_trans = today_trans + {amount} '
                                f'where `name` = "bytecoin"')

                    cur.execute('select new_transactions from users '
                                f'where id = {to}')
                    news = cur.fetchall()
                    if news and news[0]['new_transactions'] < 255:
                        cur.execute('update users set new_transactions = '
                                    f'new_transactions + 1 where id = {to}')

                    cur.execute('select transactions from ntfs_settings '
                                f'where userId = {to}')
                    tr_enabled = cur.fetchall()
                    tr_enabled = bool(tr_enabled[0]['transactions']) \
                        if tr_enabled else False

                    if vk_api.apps.isNotificationsAllowed(user_id=to)[
                            'is_allowed'] and tr_enabled:
                        user = vk_api.users.get(user_ids=[user_id],
                                                name_case='gen')[0]
                        name = ' '.join(
                            (user['first_name'], user['last_name'])
                        )
                        vk_api.notifications.sendMessage(
                            user_ids=[to],
                            message=NTF_MESSAGE.format(name=name,
                                                       amount=amount,
                                                       curr='Bytecoin`ов'),
                        )

                    print(f'{time.ctime()} - Success!\n'
                          f'\t{amount} bytecoins from id{user_id} to id{to}')

                finally:
                    return 'ok'

            else:
                bytecoin_api.send_money(user_id, amount)
                rem = {
                    'from': user_id,
                    'to': rem[0]['bytecoin_to'] if rem else None
                }
                print(f'{time.ctime()} - User or target not found!\n'
                      f'\tReturned {amount} bytecoins. Remittance - {rem}')

        return 'ok'

    except Exception as e:
        print('Bytecoin - ', e.__class__.__name__, e)
        pprint(request.json)
        return 'ok'


@app.route('/paperscroll', methods=['POST'])
def paperscroll():
    """
{
    "event": "transfer_new",
    "object": {
        "transfer_id": 37356,
        "external_id": 37357,
        "owner_id": -1,
        "peer_id": 100772411,
        "is_initiator": false,
        "payload": 100,
        "type": "transfer",
        "object_type": "balance",
        "object_type_id": 0,
        "amount": 1000,
        "create_date": 1590134400
    },
    "secret": "yQ7Z1LDDG83Q8r8Ym9Yu2aXzBc51T06Q"
}
    """
    try:
        # pprint(request.json)
        json: dict = request.json
        if json is None:
            return 'OK'

        if 'secret' not in json or json['secret'] != PS_SECRET:
            return 'OK'

        json = json['object']

        user_id = json['peer_id']
        json['amount'] /= 1000
        amount = json['amount']

        if json['object_type'] != 'balance':
            print(f'{time.ctime()} - Received unsupported paperscroll item.\n'
                  f'\tReturned: {json["object_type"]} '
                  f'{json["object_type_id"]}')
            ps_api.createTransfer(
                user_id,
                amount,
                json['object_type'],
                json['object_type_id']
            )
            return 'OK'

        with get_db() as cur:
            cur.execute('select paperscroll_to, paperscroll_time, '
                        'paperscroll_msg '
                        f'from users where id = {user_id}')
            rem = cur.fetchall()

            if rem != () and rem[0]['paperscroll_to'] is not None:
                cur.execute('update users set '
                            'paperscroll_to = null, '
                            'paperscroll_time = null, '
                            'paperscroll_msg = null '
                            f'where id = {user_id}'
                            )

                to = rem[0]['paperscroll_to']
                time_ = rem[0]['paperscroll_time']
                msg = rem[0]['paperscroll_msg'].replace('"', r'\"')

                if json['create_date'] - time_ > 900:
                    print('Remittance expired! Time passed: {}'
                          '\n\tRemittance - {}. Returned {} paper.'
                          ''.format(
                              json['create_date'] - time_,
                              rem,
                              amount
                          ))

                    ps_api.createTransfer(user_id, amount)
                    return 'OK'

                if to == 0:
                    if not cur.execute('update `bank` set '
                                       'paperscroll = '
                                       f'paperscroll + {amount} '
                                       f'where userId = {user_id}'):
                        cur.execute('insert `bank` (userId, paperscroll) '
                                    f'values ({user_id}, {amount})')

                    cur.execute('insert transactions (`from`, `to`, `time`, '
                                'currency, amount, message) values '
                                '({peer_id}, {to}, {create_date}, '
                                '"paperscroll", {amount}, "{msg}")'
                                ''.format(**json, to=to, msg=msg)
                                )
                    print(f'User {user_id} has replenished his account '
                          f'for {amount} paperscrolls.')
                    return 'OK'

                try:
                    ps_api.createTransfer(to, amount)
                except ApiError as e:
                    if e.error_code == 6:
                        print(f'{time.ctime()} - Fail.\n'
                              f'\t{e.error_text}! '
                              f'Returned {amount} paper.')

                    ps_api.createTransfer(user_id, amount)

                else:
                    cur.execute('insert transactions (`from`, `to`, `time`, '
                                'currency, amount, message) values '
                                '({peer_id}, {to}, {create_date}, '
                                '"paperscroll", {amount}, "{msg}")'
                                ''.format(**json, to=to, msg=msg)
                                )
                    cur.execute('update currencies '
                                f'set today_trans = today_trans + {amount} '
                                'where `name` = "paperscroll"')

                    cur.execute('select new_transactions from users '
                                f'where id = {to}')
                    news = cur.fetchall()
                    if news and news[0]['new_transactions'] < 255:
                        cur.execute('update users set new_transactions = '
                                    f'new_transactions + 1 where id = {to}')

                    cur.execute('select transactions from ntfs_settings '
                                f'where userId = {to}')
                    tr_enabled = cur.fetchall()
                    tr_enabled = bool(tr_enabled[0]['transactions']) \
                        if tr_enabled else False

                    if vk_api.apps.isNotificationsAllowed(user_id=to)[
                            'is_allowed'] and tr_enabled:
                        user = vk_api.users.get(user_ids=[user_id],
                                                name_case='gen')[0]
                        name = ' '.join(
                            (user['first_name'], user['last_name'])
                        )
                        vk_api.notifications.sendMessage(
                            user_ids=[to],
                            message=NTF_MESSAGE.format(name=name,
                                                       amount=amount,
                                                       curr='рулонов'),
                        )

                    print(f'{time.ctime()} - Success!\n'
                          f'\t{amount} paper from id{user_id} to id{to}')

                finally:
                    return 'OK'

            else:
                ps_api.createTransfer(user_id, amount)
                rem = {
                    'from': user_id,
                    'to': rem[0]['paperscroll_to'] if rem else None
                }
                print(f'{time.ctime()} - User or target not found!\n'
                      f'\tReturned {amount/1000} paper. Remittance - {rem}')
                return 'OK'

    except Exception as e:
        print('Paperscroll - ', e.__class__.__name__, e)
        pprint(request.json)
        return 'OK'


def coronacoin(data):
    """
    {
        amount: 1,
        from_id: 588045627,
        id: 759288,
        time: 1596745987,
        to_id: 360092594,
        type: 1
    }
    """
    try:
        user_id = data['from_id']
        data['amount'] /= 1000
        amount = data['amount']

        with get_db() as cur:
            cur.execute('select coronacoin_to, coronacoin_time, '
                        'coronacoin_msg '
                        f'from users where id = {user_id}')
            rem = cur.fetchall()

            if rem and rem[0]['coronacoin_to'] is not None:
                cur.execute('update users set '
                            'coronacoin_to = null, '
                            'coronacoin_time = null, '
                            'coronacoin_msg = null '
                            f'where id = {user_id}'
                            )

                to = rem[0]['coronacoin_to']
                time_ = rem[0]['coronacoin_time']
                msg = rem[0]['coronacoin_msg'].replace('"', r'\"')

                if data['time'] - time_ > 900:
                    print(
                        'Remittance expired! Time passed: {}'
                        '\n\tRemittance - {}. Returned {} coronacoins'
                        ''.format(
                                data['time'] - time_,
                                rem,
                                amount
                        )
                    )

                    coronacoin_api.send(user_id, amount)
                    return

                if to == 0:
                    if not cur.execute('update `bank` set '
                                       f'coronacoin = coronacoin + {amount} '
                                       f'where userId = {user_id}'):
                        cur.execute('insert `bank` (userId, coronacoin) '
                                    f'values ({user_id}, {amount})')

                    cur.execute('insert transactions (`from`, `to`, `time`, '
                                'currency, amount, message) values '
                                '({from_id}, 0, {time}, '
                                '"coronacoin", {amount}, "")'
                                ''.format(**data)
                                )
                    print(f'User {user_id} has replenished his account '
                          f'for {amount} coronacoins.')
                    return 'OK'

                try:
                    coronacoin_api.send(to, amount)
                except Exception as e:
                    if 'incorrect' in str(e):
                        print(f'{time.ctime()} - Fail.\n'
                              f'\tCan`t send to id{to}! '
                              f'Returned {amount} coronacoin.')

                    coronacoin_api.send(user_id, amount)

                else:
                    cur.execute('insert transactions (`from`, `to`, `time`, '
                                'currency, amount, message) values '
                                '({from_id}, {to}, {time}, '
                                '"coronacoin", {amount}, "{msg}")'
                                ''.format(**data, to=to, msg=msg)
                                )
                    cur.execute('update currencies '
                                f'set today_trans = today_trans + {amount} '
                                f'where `name` = "coronacoin"')

                    cur.execute('select new_transactions from users '
                                f'where id = {to}')
                    news = cur.fetchall()
                    if news and news[0]['new_transactions'] < 255:
                        cur.execute('update users set new_transactions = '
                                    f'new_transactions + 1 where id = {to}')

                    cur.execute('select transactions from ntfs_settings '
                                f'where userId = {to}')
                    tr_enabled = cur.fetchall()
                    tr_enabled = bool(tr_enabled[0]['transactions']) \
                        if tr_enabled else False

                    if vk_api.apps.isNotificationsAllowed(user_id=to)[
                            'is_allowed'] and tr_enabled:
                        user = vk_api.users.get(user_ids=[user_id],
                                                name_case='gen')[0]
                        name = ' '.join(
                            (user['first_name'], user['last_name'])
                        )
                        vk_api.notifications.sendMessage(
                            user_ids=[to],
                            message=NTF_MESSAGE.format(name=name,
                                                       amount=amount,
                                                       curr='Coronacoin`ов'),
                        )

                    print(f'{time.ctime()} - Success!\n'
                          f'\t{amount} coronacoins '
                          f'from id{user_id} to id{to}')

            else:
                coronacoin_api.send(user_id, amount)
                rem = {
                    'from': user_id,
                    'to': rem[0]['coronacoin_to'] if rem else None
                }
                print(f'{time.ctime()} - User or target not found!\n'
                      f'\tReturned {amount} coronacoins. '
                      f'Remittance - {rem}')

    except Exception as e:
        print('Coronacoin - ', e.__class__.__name__, e)
        pprint(data)


@app.route('/vkpoint', methods=['POST'])
def vkpoint():
    """
    {
        'object': {
            'datetime': 1597416236,
            'id': '146854',
            'peer_id': '588045627',
            'point': 1.1
        },
        'type': 'translated',
        'user_id': '360092594'
    }
    """
    try:
        json: dict = request.json
        pprint(json)
        if json is None or {'object', 'type', 'user_id'} - json.keys():
            return 'ok'

        if not isinstance(json['object'], dict) or \
                {'datetime', 'id', 'peer_id', 'point'} != \
                set(json['object'].keys()) or \
                not isinstance(json['object']['peer_id'], str) or \
                not isinstance(json['object']['point'], (int, float)):
            return 'ok'

        if json['user_id'] != str(ID):
            return 'ok'

        if json['type'] != 'translated':
            return 'ok'

        json = json['object']

        user_id = json['peer_id']
        amount = json['point']

        with get_db() as cur:
            cur.execute('select vkpoint_to, vkpoint_time, vkpoint_msg '
                        f'from users where id = {user_id}')
            rem = cur.fetchall()

            if rem != () and rem[0]['vkpoint_to'] is not None:
                cur.execute('update users set '
                            'vkpoint_to = null, '
                            'vkpoint_time = null, '
                            'vkpoint_msg = null '
                            f'where id = {user_id}'
                            )

                to = rem[0]['vkpoint_to']
                time_ = rem[0]['vkpoint_time']
                msg = rem[0]['vkpoint_msg'].replace('"', r'\"')

                if json['datetime'] - time_ > 900:
                    print(
                        'Remittance expired! Time passed: {}\n'
                        '\nRemittance - {}. Returned {} vkpoints'
                        ''.format(json['datetime'] - time_, rem, amount)
                    )

                    vkpoint_api.merchantSend(user_id, amount)
                    return 'ok'

                if to == 0:
                    if not cur.execute('update `bank` set '
                                       f'vkpoint = vkpoint + {amount} '
                                       f'where userId = {user_id}'):
                        cur.execute('insert `bank` (userId, vkpoint) '
                                    f'values ({user_id}, {amount})')

                    cur.execute('insert transactions (`from`, `to`, `time`, '
                                'currency, amount, message) values '
                                '({peer_id}, 0, {datetime}, '
                                '"vkpoint", {point}, "")'
                                ''.format(**json)
                                )
                    print(f'User {user_id} has replenished his account '
                          f'for {amount} vkpoints.')
                    return 'OK'

                try:
                    vkpoint_api.merchantSend(to, amount)
                except Exception as e:
                    print(f'Failed to remit {amount} vkpoints to {to}.\n'
                          f'\t{e.__class__.__name__} - {e}')
                    vkpoint_api.merchantSend(user_id, amount)

                else:
                    cur.execute('insert transactions (`from`, `to`, `time`, '
                                'currency, amount, message) values '
                                '({peer_id}, {to}, {datetime}, '
                                '"vkpoint", {point}, "{msg}")'
                                ''.format(**json, to=to, msg=msg)
                                )
                    cur.execute('update currencies '
                                f'set today_trans = today_trans + {amount} '
                                'where `name` = "vkpoint"')

                    cur.execute('select new_transactions from users '
                                f'where id = {to}')
                    news = cur.fetchall()
                    if news and news[0]['new_transactions'] < 255:
                        cur.execute('update users set new_transactions = '
                                    f'new_transactions + 1 where id = {to}')

                    cur.execute('select transactions from ntfs_settings '
                                f'where userId = {to}')
                    tr_enabled = cur.fetchall()
                    tr_enabled = bool(tr_enabled[0]['transactions']) \
                        if tr_enabled else False

                    if vk_api.apps.isNotificationsAllowed(user_id=to)[
                            'is_allowed'] and tr_enabled:
                        user = vk_api.users.get(user_ids=[user_id],
                                                name_case='gen')[0]
                        name = ' '.join(
                            (user['first_name'], user['last_name'])
                        )
                        vk_api.notifications.sendMessage(
                            user_ids=[to],
                            message=NTF_MESSAGE.format(name=name,
                                                       amount=amount,
                                                       curr='VK point`ов'),
                        )

                    print(f'{time.ctime()} - Success!\n'
                          f'\t{amount} vkpoints from id{user_id} to id{to}')

                finally:
                    return 'ok'

            else:
                vkpoint_api.merchantSend(user_id, amount)
                rem = {'from': user_id, 'to': rem[0]['vkpoint_to']}
                print(f'{time.ctime()} - User or target not found!\n'
                      f'\tReturned {amount} vkpoints. Remittance - {rem}')
                return 'ok'

    except Exception as e:
        print('Vkpoint - ', e.__class__.__name__, e)
        pprint(request.json)
        return 'ok'


@app.route('/catcoin', methods=['POST'])
def catcoin():
    """
    {
        id: 2627951,
        amount: 1,
        payload: 1234,
        created_at: 1555612247,
        from_id: 19039187,
        to_id: 360092594,
        key: '5bb8fcefd43242773e34eb485f377463'

        <id;from_id;amount;payload;apiKey> - md5
    }
    """
    try:
        json: dict = request.json
        pprint(json)
        if json is None:
            return 'YES'

        try:
            hash_ = '{id};{from_id};{amount};{payload};{key_}'.format(
                        **json,
                        key_=catcoin_api.token
                    )
            if md5(bytes(hash_, 'utf-8')).hexdigest() != json['key']:
                return 'YES'

        except KeyError:
            return 'YES'

        user_id = json['from_id']
        json['amount'] /= 1000
        amount = json['amount']

        with get_db() as cur:
            cur.execute('select catcoin_to, catcoin_time, catcoin_msg '
                        f'from users where id = {user_id}')
            rem = cur.fetchall()

            if rem and rem[0]['catcoin_to'] is not None:
                cur.execute('update users set '
                            'catcoin_to = null, '
                            'catcoin_time = null, '
                            'catcoin_msg = null '
                            f'where id = {user_id}'
                            )

                to = rem[0]['catcoin_to']
                time_ = rem[0]['catcoin_time']
                msg = rem[0]['catcoin_msg'].replace('"', r'\"')

                if json['created_at'] - time_ > 900:
                    print(
                        'Remittance expired! Time passed: {}'
                        '\n\tRemittance - {}. Returned {} catcoins'
                        ''.format(json['created_at'] - time_, rem, amount)
                    )

                    catcoin_api.send_money(user_id, amount)
                    return 'YES'

                if to == 0:
                    if not cur.execute('update `bank` set '
                                       f'catcoin = catcoin + {amount} '
                                       f'where userId = {user_id}'):
                        cur.execute('insert `bank` (userId, catcoin) '
                                    f'values ({user_id}, {amount})')

                    cur.execute('insert transactions (`from`, `to`, `time`, '
                                'currency, amount, message) values '
                                '({from_id}, 0, {created_at}, '
                                '"catcoin", {amount}, "")'
                                ''.format(**json)
                                )
                    print(f'User {user_id} has replenished his account '
                          f'for {amount} catcoins.')
                    return 'YES'

                try:
                    catcoin_api.send_money(to, amount)
                except Exception as e:
                    print(e)
                    catcoin_api.send_money(user_id, amount)

                else:
                    cur.execute('insert transactions (`from`, `to`, `time`, '
                                'currency, amount, message) values '
                                '({from_id}, {to}, {created_at}, '
                                '"catcoin", {amount}, "{msg}")'
                                ''.format(**json, to=to, msg=msg)
                                )
                    cur.execute('update currencies '
                                'set today_trans = today_trans + '
                                f'{amount} '
                                f'where `name` = "catcoin"')

                    cur.execute('select new_transactions from users '
                                f'where id = {to}')
                    news = cur.fetchall()
                    if news and news[0]['new_transactions'] < 255:
                        cur.execute('update users set new_transactions = '
                                    f'new_transactions + 1 where id = {to}')

                    cur.execute('select transactions from ntfs_settings '
                                f'where userId = {to}')
                    tr_enabled = cur.fetchall()
                    tr_enabled = bool(tr_enabled[0]['transactions']) \
                        if tr_enabled else False

                    if vk_api.apps.isNotificationsAllowed(user_id=to)[
                            'is_allowed'] and tr_enabled:
                        user = vk_api.users.get(user_ids=[user_id],
                                                name_case='gen')[0]
                        name = ' '.join(
                            (user['first_name'], user['last_name'])
                        )
                        vk_api.notifications.sendMessage(
                            user_ids=[to],
                            message=NTF_MESSAGE.format(name=name,
                                                       amount=amount,
                                                       curr='CatCoin`ов'),
                        )

                    print(f'{time.ctime()} - Success!\n'
                          f'\t{amount} catcoins '
                          f'from id{user_id} to id{to}')

                finally:
                    return 'YES'

            else:
                catcoin_api.send_money(user_id, amount)

                rem = {'from': user_id, 'to': rem[0]['catcoin_to']}
                print(f'{time.ctime()} - User or target not found!\n'
                      f'\tReturned {amount} catcoins. Remittance - {rem}')
                return 'YES'

    except Exception as e:
        print('Catcoin - ', e.__class__.__name__, e)
        pprint(request.json)
        return 'YES'


# @app.route('/worldcoin', methods=['POST'])
def worldcoin(json):
    """
    {
        id: 2627951,
        amount: "284.295",
        code: 1234,
        time: 1555612247,
        from: 360092594,
        to: -196159206
    }
    """
    try:
        user_id = json['from']
        json['amount'] = float(json['amount'])
        amount = json['amount']

        with get_db() as cur:
            cur.execute('select worldcoin_to, worldcoin_time, worldcoin_msg '
                        f'from users where id = {user_id}')
            rem = cur.fetchall()

            if rem and rem[0]['worldcoin_to'] is not None:
                cur.execute('update users set '
                            'worldcoin_to = null, '
                            'worldcoin_time = null, '
                            'worldcoin_msg = null '
                            f'where id = {user_id}'
                            )

                to = rem[0]['worldcoin_to']
                time_ = rem[0]['worldcoin_time']
                msg = rem[0]['worldcoin_msg'].replace('"', r'\"')

                if json['time'] - time_ > 900:
                    print(
                        'Remittance expired! Time passed: {}'
                        '\n\tRemittance - {}. Returned {} worldcoins'
                        ''.format(json['time'] - time_, rem, amount)
                    )

                    worldcoin_api.send_money(user_id, amount)
                    return 'YES'

                if to == 0:
                    if not cur.execute('update `bank` set '
                                       f'worldcoin = worldcoin + {amount} '
                                       f'where userId = {user_id}'):
                        cur.execute('insert `bank` (userId, worldcoin) '
                                    f'values ({user_id}, {amount})')

                    cur.execute('insert transactions (`from`, `to`, `time`, '
                                'currency, amount, message) values '
                                '({from}, 0, {time}, '
                                '"worldcoin", {amount}, "")'
                                ''.format(**json)
                                )
                    print(f'User {user_id} has replenished his account '
                          f'for {amount} worldcoins.')
                    return 'YES'

                try:
                    worldcoin_api.send_money(to, amount)
                except Exception as e:
                    print(e)
                    worldcoin_api.send_money(user_id, amount)

                else:
                    cur.execute('insert transactions (`from`, `to`, `time`, '
                                'currency, amount, message) values '
                                '({from}, {to}, {time}, '
                                '"worldcoin", {amount}, "{msg}")'
                                ''.format(**json, to=to, msg=msg)
                                )
                    cur.execute('update currencies '
                                'set today_trans = today_trans + '
                                f'{amount} '
                                f'where `name` = "worldcoin"')

                    cur.execute('select new_transactions from users '
                                f'where id = {to}')
                    news = cur.fetchall()
                    if news and news[0]['new_transactions'] < 255:
                        cur.execute('update users set new_transactions = '
                                    f'new_transactions + 1 where id = {to}')

                    cur.execute('select transactions from ntfs_settings '
                                f'where userId = {to}')
                    tr_enabled = cur.fetchall()
                    tr_enabled = bool(tr_enabled[0]['transactions']) \
                        if tr_enabled else False

                    if vk_api.apps.isNotificationsAllowed(user_id=to)[
                            'is_allowed'] and tr_enabled:
                        user = vk_api.users.get(user_ids=[user_id],
                                                name_case='gen')[0]
                        name = ' '.join(
                            (user['first_name'], user['last_name'])
                        )
                        vk_api.notifications.sendMessage(
                            user_ids=[to],
                            message=NTF_MESSAGE.format(name=name,
                                                       amount=amount,
                                                       curr='Worldcoin`ов'),
                        )

                    print(f'{time.ctime()} - Success!\n'
                          f'\t{amount} worldcoins '
                          f'from id{user_id} to id{to}')

                finally:
                    return 'YES'

            else:
                worldcoin_api.send_money(user_id, amount)

                rem = {'from': user_id, 'to': rem[0]['worldcoin_to']}
                print(f'{time.ctime()} - User or target not found!\n'
                      f'\tReturned {amount} worldcoins. Remittance - {rem}')
                return 'YES'

    except Exception as e:
        print('Worldcoin - ', e.__class__.__name__, e)
        pprint(request.json)
        return 'YES'


def calc_rates():
    with get_db() as cur:
        cur.execute('select `name`, factor, today_trans, yest_trans '
                    'from currencies')
        currs = cur.fetchall()
        for c in currs:
            today = c['today_trans']
            yest = c['yest_trans']
            if today == 0 and yest == 0:
                cur.execute('update currencies '
                            'set yest_price = price '
                            f'where `name` = "{c["name"]}"')
                continue
            if today == 0:
                today = yest * 0.55
            elif yest == 0:
                yest = today * 0.55

            mult = (yest / today) ** c['factor']
            cur.execute('update currencies '
                        f'set yest_price = price, price = price / {mult}, '
                        f'yest_trans = today_trans, today_trans = 0 '
                        f'where `name` = "{c["name"]}"')


name_sched = BackgroundScheduler()
name_sched.add_job(
    set_service_name,
    'interval',
    hours=4.5
)

coronacoin_sched = BackgroundScheduler()
try:
    cc_last_trans = coronacoin_api.history()[0]['id']
except (ConnectionError, JSONDecodeError, ReadTimeout):
    cc_last_trans = None
    print("Can't connect to coronacoin")
else:
    def coronacoin_check():
        global cc_last_trans
        try:
            new_rems = []
            hist = coronacoin_api.history()
            for tr in hist:
                if tr['id'] == cc_last_trans:
                    cc_last_trans = hist[0]['id']
                    break
                else:
                    new_rems.append(tr)

            for i in range(len(new_rems) - 1, -1, -1):
                coronacoin(new_rems[i])

        except ConnectionError:
            pass

        except Exception as e:
            print('Coronacoin check - ', e.__class__.__name__, e)


    coronacoin_sched.add_job(
        coronacoin_check,
        'interval',
        seconds=10,
        max_instances=3,
    )

worldcoin_sched = BackgroundScheduler()
try:
    wc_last_trans = worldcoin_api.history(1)[0]['id']
except (ConnectionError, JSONDecodeError, ReadTimeout):
    wc_last_trans = None
    print("Can't connect to worldcoin")
else:
    def worldcoin_check():
        global wc_last_trans
        try:
            new_rems = []
            hist = worldcoin_api.history(1)
            for tr in hist:
                if tr['id'] == wc_last_trans:
                    wc_last_trans = hist[0]['id']
                    break
                else:
                    new_rems.append(tr)

            for i in range(len(new_rems) - 1, -1, -1):
                worldcoin(new_rems[i])

        except ConnectionError:
            pass

        except Exception as e:
            print('Worldcoin check - ', e.__class__.__name__, e)

        finally:
            time.sleep(5)

    worldcoin_sched.add_job(
        worldcoin_check,
        'interval',
        seconds=10,
        max_instances=3,
    )

rates_sched = BackgroundScheduler()
rates_sched.add_job(
    calc_rates,
    'interval',
    days=1,
    start_date=datetime.datetime.now().replace(
        hour=0, minute=0, second=0, microsecond=0
    ) + datetime.timedelta(days=1)
)


name_sched.start()
atexit.register(lambda: name_sched.shutdown(wait=False))

if cc_last_trans is not None:
    coronacoin_sched.start()
    atexit.register(lambda: coronacoin_sched.shutdown(wait=False))
if wc_last_trans is not None:
    worldcoin_sched.start()
    atexit.register(lambda: worldcoin_sched.shutdown(wait=False))

rates_sched.start()
atexit.register(rates_sched.shutdown)

app.run(host='0.0.0.0', port=5001, debug=True, use_reloader=False)
