import requests
from cryptography.fernet import Fernet

from main import ENCRYPT_KEY

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось!',
    'reviewing': 'Прямо сейчас работу проверяет ревьюер.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}

fernet = Fernet(ENCRYPT_KEY)


def encrypt(token):
    """Шифрует предоставленный токен от API Практикума."""
    return fernet.encrypt(token.encode()).decode()


def decrypt(token):
    """Дешифрует предоставленный токен от API Практикума."""
    return fernet.decrypt(token).decode()


def get_api_answer(token, timestamp):
    """Обращается к API Практикума за статусом работы на код-ревью."""
    endpoint = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
    headers = {'Authorization': f'OAuth {token}'}
    payload = {'from_date': timestamp}
    try:
        homework_status = requests.get(
            endpoint, headers=headers, params=payload, timeout=3
        )
    except Exception as error:
        raise ConnectionError(f'API connection error: {error}')
    return homework_status.json()


def check_response(response):
    """Проверяет ответ API на консистентность."""
    if not isinstance(response, dict):
        return False
    if response.get('current_date') is None:
        return False
    if response.get('homeworks') is None:
        return False
    if not isinstance(response.get('homeworks'), list):
        return False
    return True


def parse_status(api_answer):
    """Извлекает из ответа API название, статус и комментарий к работе."""
    homework = api_answer.get('homeworks')[0]
    homework_name = homework.get('lesson_name')
    verdict = HOMEWORK_VERDICTS.get(homework.get('status'))
    comment = homework.get('reviewer_comment')
    return homework_name, verdict, comment
