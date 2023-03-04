import logging

# Конфигурация логов
logging.basicConfig(
    level=logging.WARNING,
    filename="db/mylog.log",
    format="%(asctime)s %(levelname)s - %(module)s:%(lineno)d"
    " (%(funcName)s) - %(message)s",
    datefmt='%d-%b-%Y %H:%M:%S',
)


def log(message, script):
    """Обрабатывает данные пользователя из сообщения, чтобы добавить
    идентификацию в лог вместе с комментарием совершенного действия.
    """
    return (
        f"User <{message.chat.id}> [{message.from_user.username}, "
        f"{message.from_user.first_name}]: {script}"
    )
