def _get_exception_error(context, chat_id):
    """Отправка сообщения при возникновении ошибки."""
    context.bot.send_message(
            chat_id=chat_id,
            text='Возникла непредвиденная ошибка повторите попытку позже.'
        )