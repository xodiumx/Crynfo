import requests
import logging
import requests
import os
import sys

from dotenv import load_dotenv
from exceptions import APIError
from valid_codes import valid_codes
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    Filters,
    MessageHandler,
    Updater,
)
from logger import logs

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
API_TOKEN = os.getenv('API_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

HEADERS = {'X-CoinAPI-Key': API_TOKEN}


def start(update, _):
    """Приветственная комманда"""
    update.message.reply_text('Привет! Я криптобот и я могу поделиться с тобой'
                              ' некоторой информацией о криптовалютах: '
                              '`/help`- информация о доступных функциях')


def help_command(update, _):
    """Комманда /help"""
    update.message.reply_text('Используйте `/popular`, '
                              'что бы узнать цену одной из популярных валют.'
                              )
    update.message.reply_text('Если необходимой валюты нету в списке '
                              'напишите коды валют, '
                              'информация о которых вам необходима. '
                              'Например "BTC/USD", "ETH/BTC"'
                              )


def popular(update, _):
    """Комманда /popular"""
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


def get_price_of_populars(update, _) -> str:
    """Узнать цену одной из популярных валют."""
    query = update.callback_query
    code_of_currency = query.data

    endpoint = f'https://rest.coinapi.io/v1/exchangerate/{code_of_currency}/USD'
    response = requests.get(endpoint, headers=HEADERS).json()

    price = response.get('rate')

    query.answer()

    query.edit_message_text(
        text=f'На данный момент цена '
        f'{code_of_currency} составляет: {price} - USD'
    )


def get_price_with_message(update, context) -> str:
    """Извлекаем коды валют из сообщения и передаем их в ENDPOINT,
    если сообщение не валидно, предупреждаем пользователя об этом.
    """
    chat = update.message
    mesg_of_user = chat['text'].split('/')
    codes = [i for i in mesg_of_user if i in valid_codes]

    if len(mesg_of_user) != 2:
        context.bot.send_message(chat_id=CHAT_ID,
                                 text='Данные введены не правильно '
                                      '"попробуйте формат BTC/USD, '
                                      'коды должны быть заглавными символами'
                                      'и в верном формате"',
                                 )
    else:
        try:
            endpoint = f'https://rest.coinapi.io/v1/exchangerate/{codes[0]}/{codes[1]}'
            response = requests.get(endpoint, headers=HEADERS).json()
            price = response.get('rate')
            context.bot.send_message(
                chat_id=CHAT_ID,
                text=f'На данный момент цена {codes[0]} '
                     f'составляет: {price} - {codes[1]}',
            )

        except Exception as error:
            context.bot.send_message(
                chat_id=CHAT_ID,
                text='Возможно я еще, необладаю инфомацией о данной валюте, '
                     'но обещаю я скоро ее найду =)',
            )
            raise APIError(
                f'Не получилось запросить информацию от API {error}')
        

def check_tokens() -> bool:
    """Проверка доступности переменных окружения."""
    return all((API_TOKEN, CHAT_ID, TELEGRAM_TOKEN))


def main():
    """Основная логика бота."""
    if not check_tokens():
        logging.critical('Отсутствует обязательная переменная окружения')
        sys.exit('Заполните все переменные окружения')

    updater = Updater(token=TELEGRAM_TOKEN)
    app = updater.dispatcher

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('popular', popular))
    app.add_handler(CallbackQueryHandler(get_price_of_populars))
    app.add_handler(MessageHandler(Filters.text, get_price_with_message))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    logs()
    main()
