import logging
import requests
import time
from dotenv import load_dotenv
import os
import telegram
from http import HTTPStatus
import sys
import threading
import enum
from exceptions import (
    APIResponseError, APIStatusCodeError,
    YandeksError, TelegramError
)


class State(enum.Enum):
    """Класс состояний."""

    INITIAL = 0
    RUNNING = 1
    STOPPED = 2


state = State.INITIAL
state_lock = threading.Lock()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGA_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('MY_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляем сообщение в телеграм пользователю."""
    try:
        logging.info(
            'Отправляем сообщение в телеграм: %s', message
        )
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        raise TelegramError(
            f'Ошибка отправки сообщения в телеграм: {error}'
        ) from error
    else:
        logging.info('Сообщение в телеграм успешно отправленно')


def get_api_answer(current_timestamp):
    """Делаем запрос к Яндекс Апи и возвращаем ответ."""
    try:
        logging.info(
            'Делаем запрос по статусу заданий с временной меткой %s',
            current_timestamp
        )
        timestamp = current_timestamp or int(time.time())
        params = {'from_date': timestamp}
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            raise APIStatusCodeError(
                'Неверный ответ сервера: '
                f'http code = {response.status_code}; '
                f'reason = {response.reason}; '
                f'content = {response.text}'
            )
        response = response.json()
    except Exception as error:
        raise YandeksError(
            'Ошибка подключения к Яндекс Практикуму'
        ) from error
    else:
        return response


def check_response(response):
    """Функция проверяет ответ yandex practicum на корректность."""
    if not isinstance(response, dict) or response is None:
        message = 'Ответ API не содержит словаря с данными'
        raise TypeError(message)

    elif any([response.get('homeworks') is None,
              response.get('current_date') is None]):
        message = ('Словарь ответа API не содержит ключей homeworks и/или '
                   'current_date')
        raise KeyError(message)

    elif not isinstance(response.get('homeworks'), list):
        message = 'Ключ homeworks в ответе API не содержит списка'
        raise TypeError(message)

    elif not response.get('homeworks'):
        logging.debug('Статус проверки не изменился')
        return []

    else:
        return response['homeworks']


def parse_status(homework):
    """Функция возвращает ответ API yandex practicum со статусом проверки."""
    if homework.get('homework_name') is None:
        message = 'Словарь ответа API не содержит ключа homework_name'
        raise KeyError(message)
    elif homework.get('status') is None:
        message = 'Словарь ответа API не содержит ключа status'
        raise KeyError(message)
    homework_name = homework['homework_name']
    homework_status = homework['status']

    if homework_status in HOMEWORK_STATUSES:
        verdict = HOMEWORK_STATUSES[homework_status]
    else:
        message = 'Статус ответа не известен'
        raise APIResponseError(message)

    message = (f'Изменился статус проверки работы "{homework_name}".'
               f' {verdict}')
    logging.debug(message)
    return message


def check_tokens():
    """Проверяет наличие всех переменных окружения."""
    return all((
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID
    ))


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        error_message = (
            'Отсутсвтуют обязательные переменные окружения: '
            'PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID. '
            'Программа принудительно остановлена'
        )
        logging.critical(error_message)
        sys.exit(error_message)

    global state
    with state_lock:
        state = State.RUNNING

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    status_old = None
    while True:
        with state_lock:
            if state == State.STOPPED:
                break

        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            status = parse_status(homework)
            if status != status_old:
                send_message(bot, status)
                status_old = status
            current_timestamp = response.get('current_date')
        except TelegramError as error:
            error_message = f'Сбой в работе программы: {error}'
            logging.exception(error_message)
        time.sleep(RETRY_TIME)


def repl():
    """Создаем цикл с командой для остановки."""
    global state
    while True:
        command = input('Please, press "s" to stop')
        if command == 's':
            with state_lock:
                state = State.STOPPED
            break


if __name__ == '__main__':
    log_format = (
        '%(asctime)s [%(levelname)s] - '
        '(%(filename)s).%(funcName)s:%(lineno)d - %(message)s'
    )
    log_file = os.path.join(BASE_DIR, 'output.log')
    log_stream = sys.stdout
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(log_stream)
        ]
    )

    repl_thread = threading.Thread(target=repl)
    repl_thread.start()
    main()
