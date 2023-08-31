from random import randint

from Connections import vkcoin_profile, bytecoin_profile


def vkcoin_rem(to, amount):
    try:
        payload = randint(-2000000000, 2000000000)
        return f'https://vk.com/coin#x{to}_{amount*1000}_{payload}'

    except Exception:
        return ''


def bytecoin_rem(to, amount):
    try:
        return f'https://vk.com/app6948819' \
               f'#transfer_user=id{to}&sum={amount}&fixed=1'

    except Exception:
        return ''
