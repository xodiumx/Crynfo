import logging
import os
import sys
import time
import requests

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (CallbackQueryHandler, CommandHandler, Filters,
                          MessageHandler, Updater)
from exceptions import APIError, GetPriceError, NotValidCurrencyError
from logger import logs
from valid_codes import valid_codes
from utills import _get_exception_error

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
API_TOKEN = os.getenv('API_TOKEN')
PORT = int(os.environ.get('PORT', '88'))

HEADERS = {'X-CoinAPI-Key': API_TOKEN}


def start(update, _):
    """Greeting command /start"""
    name = update.message.chat.first_name
    update.message.reply_text(
        f'Привет {name}! Я криптобот и я могу поделиться'
        f' с тобой некоторой информацией о криптовалютах:\n'
        f' `/help`- информация о доступных функциях')


def help_command(update, _):
    """Command /help"""
    update.message.reply_text('Используйте `/popular`, '
                              'что бы узнать цену одной из популярных валют.'
                              )
    update.message.reply_text('Используйте `/exchanges`, '
                              'что бы узнать информацию о топ-6 биржах'
                              )
    update.message.reply_text('Если необходимой валюты нету в списке '
                              'напишите коды валют, '
                              'информация о которых вам необходима.\n'
                              'Например "BTC-USD", "ETH-BTC"'
                              )
    update.message.reply_text('Вы можете настроить предупреждение о '
                              'достижении монетой определенного уровня цены.\n'
                              'Для начала проверьте цену текстовой командой:\n'
                              'например BTC-USD, ETH-BTC, LTC-USD\nа затем '
                              'напишите команду в формате:\n'
                              '"BTC-USD-необходимая цена-warn"\n'
                              'запрос цены производится каждые 15 минут.'
                              )


def popular(update, _):
    """Command /popular"""
    keyboard = [
        [InlineKeyboardButton("BTC", callback_data='BTC')],
        [InlineKeyboardButton("ETH", callback_data='ETH')],
        [InlineKeyboardButton("BNB", callback_data='BNB')],
        [InlineKeyboardButton("XRP", callback_data='XRP')],
        [InlineKeyboardButton("DOGE", callback_data='DOGE')],
        [InlineKeyboardButton("ADA", callback_data='ADA')],
        [InlineKeyboardButton("TRX", callback_data='TRX')],
        [InlineKeyboardButton("LTC", callback_data='LTC')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        'Пожалуйста, выберите:',
        reply_markup=reply_markup
    )


def exchanges(update, _):
    """Command top exchanges /exchanges"""
    keyboard = [
        [InlineKeyboardButton("BINANCE", callback_data='exch_1')],
        [InlineKeyboardButton("COINBASE", callback_data='exch_2')],
        [InlineKeyboardButton("KRAKEN", callback_data='exch_3')],
        [InlineKeyboardButton("KUCOIN", callback_data='exch_4')],
        [InlineKeyboardButton("GEMINI", callback_data='exch_5')],
        [InlineKeyboardButton("BITFINEX", callback_data='exch_6')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text(
        'Пожалуйста, выберите:',
        reply_markup=reply_markup
    )


def get_exchange(update, context):
    """
    - Находим в списке сallback_data, сравниваем с выбором пользователя,
      если одинаково достаем название биржи
    - присваиваем название биржи переменной exc,
    - делаем запрос к API и достаем нужную информацию.
    """
    query = update.callback_query
    callback_data = query.data
    chat_id = query['message']['chat']['id']
    user_answer_data = query['message']['reply_markup']['inline_keyboard']

    for elem in user_answer_data:
        if elem[0]['callback_data'] == callback_data:
            exc = elem[0]['text']
            break
    
    endpoint = f'https://rest.coinapi.io/v1/exchanges?filter_exchange_id={exc}'
    
    try:
        response = requests.get(endpoint, headers=HEADERS).json()[0]

        exchange = response.get('exchange_id')
        opened = response.get('data_start')
        volume_mth = response.get('volume_1mth_usd')
        site = response.get('website')

    except Exception as error:
        _get_exception_error(context, chat_id)
        raise APIError(
            f'Не получилось запросить информацию от API {error}')

    query.answer()

    query.edit_message_text(
        text=f'Биржа - {exchange}\nОткрыта - {opened}\n'
             f'Объем торгов за месяц составляет: {volume_mth:_} - USD\n'
             f'Website - {site}'
    )


def get_price_of_populars(update, context) -> str:
    """Узнать цену одной из популярных валют."""
    query = update.callback_query
    chat_id = query['message']['chat']['id']
    code_of_currency = query.data
    
    endpoint = f'https://rest.coinapi.io/v1/exchangerate/{code_of_currency}/USD'
    
    try:
        response = requests.get(endpoint, headers=HEADERS).json()
        price = response.get('rate')
        if price is not None:
            price = round(price, 3)
        else:
            _get_exception_error(context, chat_id)

    except Exception as error:
        _get_exception_error(context, chat_id)
        raise APIError(
            f'Не получилось запросить информацию от API {error}')

    query.answer()

    query.edit_message_text(
        text=f'На данный момент цена '
        f'{code_of_currency} составляет: {price} - USD'
    )


def get_price_with_message(context, message: list, chat_id: int) -> str:
    """
    Передаем коды из сообщения в ENDPOINT, 
    если сообщение не валидно предупреждаем пользователя об этом.
    """
    codes = [i for i in message if i in valid_codes]

    if len(codes) != 2:
        context.bot.send_message(
            chat_id=chat_id,
            text='Данные введены не правильно '
                '"попробуйте BTC-USD, '
                'коды должны быть заглавными символами'
                ' и в верном формате"',
            )
    else:
        try:
            endpoint = f'https://rest.coinapi.io/v1/exchangerate/{codes[0]}/{codes[1]}'
            response = requests.get(endpoint, headers=HEADERS).json()
            if codes[1] in ('USD', 'USDT', 'USDC'):
                price = response.get('rate')
                if price is not None:
                    price = round(price, 3)
                else:
                    _get_exception_error(context, chat_id)
            else:
                price = response.get('rate')

            context.bot.send_message(
                chat_id=chat_id,
                text=f'На данный момент цена {codes[0]} '
                     f'составляет: {price} - {codes[1]}',
            )
        except Exception as error:
            _get_exception_error(context, chat_id)
            raise APIError(
                f'Не получилось запросить информацию от API {error}')


def get_alarm(context, message:list , chat_id: int):
    """
    Текстовая команда для установки оповещения на определенный уровень цены
    - Запрос к endpoint-у происходит каждые 15 минут
    - Если команда введена не верно происходит оповещение пользователя
    - Перед входом в цикл происходит проверка текущего уровня цены и ожидаемого
      если пользователь ожидает повышение цены, будет производиться проверка
      до момента, когда цена поднимется на ожидаемый уровень и наоборот.
    """
    fir_code = message[0]
    sec_code = message[1]
    user_price_level = int(message[2])
    time_to_request = 900

    try:
        if not isinstance(user_price_level, int):
            ...
    except Exception:
        context.bot.send_message(
            chat_id=chat_id,
            text='Введено не правильное числовое значение '
                'повторите попытку.'
            )
        raise ValueError('Введено не числовое значение')

    if fir_code and sec_code not in valid_codes:
        context.bot.send_message(
            chat_id=chat_id,
            text='Возможно данные валюты не поддерживаются '
                'или команда была записана не верно '
                'воспользуйтесь командой `/help` и повторите попытку'
            )
        raise NotValidCurrencyError('Не валидные валюты')

    endpoint = f'https://rest.coinapi.io/v1/exchangerate/{fir_code}/{sec_code}'

    context.bot.send_message(
        chat_id=chat_id,
        text='Когда цена достигнет необходимого уровня, '
             'вам прийдет оповещение.'
        )

    response = requests.get(endpoint, headers=HEADERS).json()
    current_price = int(response.get('rate'))

    if current_price < user_price_level:
        try:
            while True:
                response = requests.get(endpoint, headers=HEADERS).json()
                current_price = int(response.get('rate'))

                if current_price >= user_price_level:
                    context.bot.send_message(
                        chat_id=chat_id,
                        text=f'Цена {fir_code} поднялась до уровня\n'
                            f'{current_price} - {sec_code}'
                        )
                    break
                time.sleep(time_to_request)
        except Exception:
            _get_exception_error(context, chat_id)
            raise GetPriceError('Не получилось запросить информацию о цене.')
    else:
        try:
            while True:
                response = requests.get(endpoint, headers=HEADERS).json()
                current_price = int(response.get('rate'))

                if current_price <= user_price_level:
                    context.bot.send_message(
                    chat_id=chat_id,
                    text=f'Цена {fir_code} опустилась до уровня\n'
                        f'{current_price} - {sec_code}'
                    )
                    break
                time.sleep(time_to_request)
        except Exception:
            _get_exception_error(context, chat_id)
            raise GetPriceError('Не получилось запросить информацию о цене.')


def messages(update, context):
    """Обработчик сообщений."""
    chat = update.message
    chat_id = chat['chat']['id']
    mesg_of_user = chat['text'].split('-')

    if 'warn' in mesg_of_user:
        get_alarm(context, mesg_of_user, chat_id)
    else:
        get_price_with_message(context, mesg_of_user, chat_id)


def check_tokens() -> bool:
    """Проверка доступности переменных окружения."""
    return all((API_TOKEN, TELEGRAM_TOKEN, PORT))


def main():
    """Основная логика бота."""
    if not check_tokens():
        logging.critical('Отсутствует обязательная переменная окружения')
        sys.exit('Заполните все переменные окружения')

    updater = Updater(token=TELEGRAM_TOKEN)
    app = updater.dispatcher

    try:
        app.add_handler(CommandHandler('start', start))
        app.add_handler(CommandHandler('help', help_command))
        app.add_handler(CommandHandler('popular', popular))
        app.add_handler(CommandHandler('exchanges', exchanges))
        app.add_handler(CallbackQueryHandler(get_exchange, pattern=r'exch_\d'))
        app.add_handler(CallbackQueryHandler(get_price_of_populars))
        app.add_handler(MessageHandler(Filters.text, messages))
    except Exception as error:
        logging.error(f'Возникла ошибка в работе программы {error}')


    updater.start_webhook(
        listen='0.0.0.0',
        port=PORT,
        url_path=TELEGRAM_TOKEN,
        webhook_url=f'https://crynfo.onrender.com/{TELEGRAM_TOKEN}')
    updater.idle()


if __name__ == '__main__':
    logs()
    main()
