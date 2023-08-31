import sys
import random

price = float(input('Начальная цена: '))
factor = float(input('Коэффициент: '))
days = int(input('Сколько дней симулируем?: '))

min_sum = float(input('Минимальная сумма перевода: '))
max_sum = float(input('Максимальная сумма перевода: '))

min_trans = float(input('Минимальное кол-во переводов за день: '))
max_trans = float(input('Максимальное кол-во переводов за день: '))

log = open('./Formula tests.txt', 'w', encoding='UTF-8')
sys.stdout = log

print(f'Начальная цена: {price}')
print(f'Коэффициент: {factor}')
print(f'\nСумма переводов от {min_sum} до {max_sum}.')
print(f'Кол-во переводов за день от {min_trans} до {max_trans}.')
print(f'\nСимуляция {days} дней ...')

def day(ratio_):
    global price
    price *= ratio_ * factor + (1 - factor)
    return price


def gen_transactions():
    length = random.randint(1, 15)
    trans = [round(random.triangular(min_sum, max_sum, min_sum * 10), 3)
             for _ in range(length)]
    return trans


today = gen_transactions()
for d in range(days):
    print(f'\n\n[День {d+1}]')
    yest = today
    today = gen_transactions()
    print(f'Вчера перевели {round(sum(yest), 3)}.')
    print(f'Сегодня перевели {round(sum(today), 3)}.')
    ratio = round(round(sum(today)) / round(sum(yest)), 3)
    print(f'Сегодня перевели в {ratio} раз больше чем вчера.\n')

    print(f'Прошлая цена: {price}')
    print(f'Текущая цена: {day(ratio)}')
