import logging
from logging.handlers import RotatingFileHandler

# Конфигурация логов
logging.basicConfig(
    level=logging.ERROR,
    handlers=[
        RotatingFileHandler('db/bot57.log', maxBytes=5000000, backupCount=10)
    ],
    format="%(asctime)s %(levelname)s - %(module)s:%(lineno)d"
    " (%(funcName)s) - %(message)s",
    datefmt='%d-%b-%Y %H:%M:%S',
)

formatter = logging.Formatter(
    "%(asctime)s %(levelname)s - %(module)s:%(lineno)d"
    " (%(funcName)s) - %(message)s",
    datefmt='%d-%b-%Y %H:%M:%S',
)

# Отдельный кастомный логгер в файл logs.log для пользовательских событий
logger = logging.getLogger('Warning_logger')
warning_handler = logging.FileHandler('db/logs.log')
logger.setLevel(logging.WARNING)
logger.addHandler(warning_handler)
warning_handler.setFormatter(formatter)


def log(message, script):
    """Обрабатывает данные пользователя из сообщения, чтобы добавить
    идентификацию в лог вместе с комментарием совершенного действия.
    """
    return (
        f"User <{message.chat.id}> [{message.from_user.username}, "
        f"{message.from_user.first_name}]: {script}"
    )
