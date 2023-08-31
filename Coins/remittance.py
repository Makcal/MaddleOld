from Connections import (vkcoin_api, bytecoin_api, ps_api, coronacoin_api,
                         vkpoint_api, catcoin_api, worldcoin_api)


def vkcoin_rem(amount):
    try:
        return vkcoin_api.get_payment_url(amount)
    except Exception as e:
        print('VKcoin link -', e.__class__.__name__, e)
        return ''


def bytecoin_rem(amount):
    try:
        return bytecoin_api.get_payment_url(amount)
    except Exception as e:
        print('Bytecoin link -', e.__class__.__name__, e)
        return ''


def paperscroll_rem(amount):
    try:
        return ps_api.getLink(amount)
    except Exception as e:
        print('Paperscroll link -', e.__class__.__name__, e)
        return ''


def coronacoin_rem(amount):
    try:
        return coronacoin_api.get_link(amount * 1000)
    except Exception as e:
        print('Coronacoin link -', e.__class__.__name__, e)
        return ''


def vkpoint_rem(amount):
    try:
        return vkpoint_api.getLink(amount)
    except Exception as e:
        print('Vkpoint link -', e.__class__.__name__, e)
        return ''


def catcoin_rem(amount):
    try:
        return catcoin_api.make_link(amount)
    except Exception as e:
        print('Catcoin link -', e.__class__.__name__, e)
        return ''


def worldcoin_rem(amount):
    try:
        return worldcoin_api.make_link(amount)
    except Exception as e:
        print('Worldcoin link -', e.__class__.__name__, e)
        return ''
