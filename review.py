import asyncio

import aiohttp
import requests
from cryptography.fernet import Fernet

from main import ENCRYPT_KEY

ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось!',
    'reviewing': 'Прямо сейчас работу проверяет ревьюер.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}

fernet = Fernet(ENCRYPT_KEY)


async def get_multiple_api(tokens):
    """Асинхронная функция для получения ответов от API Практикума по списку
    предоставленных токенов.
    """
    tasks = []
    async with aiohttp.ClientSession() as session:
        for token, timestamp in tokens:
            headers = {'Authorization': f'OAuth {token}'}
            payload = {'from_date': timestamp}
            tasks.append(
                asyncio.create_task(
                    session.get(
                        ENDPOINT, headers=headers, params=payload, timeout=3
                    )
                )
            )
        responses = await asyncio.gather(*tasks)
    results = []
    for response in responses:
        response.raise_for_status()
        results.append(await response.json())
    return results


def get_api_answer(token, timestamp):
    """Обращается к API Практикума за статусом работы на код-ревью."""
    headers = {'Authorization': f'OAuth {token}'}
    payload = {'from_date': timestamp}
    try:
        homework_status = requests.get(
            ENDPOINT, headers=headers, params=payload, timeout=3
        )
    except Exception as error:
        raise ConnectionError(f'API connection error: {error}')
    return homework_status.json()


def encrypt(token):
    """Шифрует предоставленный токен от API Практикума."""
    return fernet.encrypt(token.encode()).decode()


def decrypt(token):
    """Дешифрует предоставленный токен от API Практикума."""
    return fernet.decrypt(token).decode()


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
