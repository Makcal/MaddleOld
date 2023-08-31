from my_utils import get_db


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


calc_rates()
