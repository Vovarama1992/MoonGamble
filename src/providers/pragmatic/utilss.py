import aiohttp
import backoff
from fastapi import HTTPException
import hashlib
import hmac
import time
import random
from urllib.parse import urlencode
import logging
from src.settings import Settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - src.providers.pragmatic.utils - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def generate_headers_and_sign(params: dict):
    # Генерация X-Nonce с использованием md5
    nonce = hashlib.md5(str(random.getrandbits(128)).encode('utf-8')).hexdigest()
    timestamp = str(int(time.time()))  # Используем время в секундах

    merchant_key = Settings.PRAGMATIC_MERCHANT_KEY

    # Логируем ключ полностью
    logger.info(f"Merchant Key используется для подписи: {merchant_key}")

    headers = {
        "X-Merchant-Id": Settings.PRAGMATIC_MERCHANT_ID,
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
    }

    # Добавляем поле session_id, в котором используется тот же таймстемп
    params["session_id"] = f"session-{timestamp}"

    # Объединяем параметры тела и заголовков для генерации подписи
    merged_params = {**params, **headers}

    # Логируем массив до сортировки
    logger.info(f"Массив после объединения, до сортировки: {merged_params}")

    # Сортировка параметров по ключу
    sorted_params = sorted(merged_params.items())

    # Логируем массив после сортировки
    logger.info(f"Массив после сортировки: {sorted_params}")

    # Генерация строки для подписи
    hash_string = urlencode(sorted_params)

    # Логируем строку для подписи
    logger.info(f"Строка для подписи: {hash_string}")

    # Генерация подписи HMAC-SHA1 с использованием Merchant Key
    sign = hmac.new(merchant_key.encode(), hash_string.encode(), hashlib.sha1).hexdigest()

    # Логируем сгенерированную подпись
    logger.info(f"Сгенерированная подпись: {sign}")

    # Добавляем подпись в заголовки
    headers["X-Sign"] = sign

    return headers

async def handle_response(response):
    try:
        response_data = await response.json()
        logger.info(f"Ответ сервера: {response_data}")
    except Exception as e:
        logger.error(f"Не удалось получить JSON из ответа: {e}")
        response_data = {"detail": "Не удалось распарсить ответ"}

    logger.info(f"Заголовки ответа: {response.headers}")

    if response.status == 200:
        return response_data
    elif response.status == 403:
        logger.error(f"Ошибка 403: Forbidden, ответ: {response_data}")
        raise HTTPException(status_code=403, detail=f"Forbidden: {response_data}")
    else:
        raise HTTPException(status_code=response.status, detail=f"Error: {response_data}")

@backoff.on_exception(backoff.expo, (aiohttp.ClientError, aiohttp.ClientResponseError),
                      max_tries=3,
                      giveup=lambda e: e.status not in [429, 430, 500, 503])
async def make_request(method: str, endpoint: str, data: dict = None):
    url = f"{Settings.PRAGMATIC_BASE_API_URL}/{endpoint}"

    # Если данные не переданы, создаем пустой словарь
    if data is None:
        data = {}

    # Удаляем None параметры или пустые строки
    filtered_data = {k: v for k, v in data.items() if v is not None and v != ""}

    # Генерация заголовков и подписи
    headers = generate_headers_and_sign(filtered_data)

    async with aiohttp.ClientSession() as session:
        if method == "POST":
            # Формируем URL с параметрами для POST-запроса
            post_data = urlencode(filtered_data)
            url = f"{url}?{post_data}"
            # Логируем запрос
            logger.info(f"Отправка запроса на {url} с методом {method} и заголовками: {headers}")
            async with session.post(url, headers=headers) as response:
                return await handle_response(response)
        elif method == "GET":
            # Формируем URL с параметрами для GET-запроса
            query_string = urlencode(filtered_data)
            url = f"{url}?{query_string}"
            logger.info(f"GET запрос: URL {url}")
            async with session.get(url, headers=headers) as response:
                return await handle_response(response)
        else:
            raise aiohttp.web.HTTPMethodNotAllowed(method, allowed_methods=["POST", "GET"])
