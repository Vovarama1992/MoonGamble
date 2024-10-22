import aiohttp
import hashlib
import time
import hmac
import urllib.parse
import uuid

url = "https://staging.gamerouter.pw/api/index.php/v1/"

# Жестко закодированные значения для self-validate
merchant_id_self_validate = "506866590132dcf90a48f0d66727a3d4"
merchant_key_self_validate = "7b05548b6df95ace55877d34781441174ced8d8e"

# Храним уникальные transaction_id, чтобы избежать дублирования
processed_transactions = set()

async def make_request(method: str, endpoint: str, data: dict, headers: dict = None):
    print(f"Method: {method}")
    print(f"Endpoint: {endpoint}")
    print(f"Data: {data}")

    current_time = str(int(time.time()))
    nonce = hashlib.md5(str(uuid.uuid4()).encode("utf-8")).hexdigest()

    if endpoint == "self-validate":
        # Для self-validate используем жестко закодированные заголовки
        merchant_id = merchant_id_self_validate
        merchant_key = merchant_key_self_validate

        base_headers = {
            "X-Merchant-Id": merchant_id,
            "X-Timestamp": current_time,
            "X-Nonce": nonce,
        }

        # Подпись для self-validate
        merged_params = {**data, **base_headers}
        sorted_params = dict(sorted(merged_params.items()))
        hash_string = urllib.parse.urlencode(sorted_params)
        x_sign = hmac.new(merchant_key.encode("utf-8"), hash_string.encode("utf-8"), hashlib.sha1).hexdigest()

        post_data = urllib.parse.urlencode(data)

        async with aiohttp.ClientSession() as session:
            async with session.post(url + endpoint, headers={
                **base_headers,
                "X-Sign": x_sign,
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            }, data=post_data) as response:
                result = await response.text()
                print("Response:", result)

                try:
                    return await response.json()
                except Exception as e:
                    print(f"Failed to parse JSON: {e}")
                    return {"error": "Invalid response format"}
    else:
        # Для balance, bet, refund, win используем заголовки из параметров (если переданы)
        merchant_id = headers.get("X-Merchant-Id") if headers and "X-Merchant-Id" in headers else None

        base_headers = {
            "X-Timestamp": current_time,
            "X-Nonce": nonce,
        }

        # Если был передан merchant_id в заголовках — добавляем его
        if merchant_id:
            base_headers["X-Merchant-Id"] = merchant_id

        # Подпись для balance, bet, refund, win
        merged_params = {**data, **base_headers}
        sorted_params = dict(sorted(merged_params.items()))
        hash_string = urllib.parse.urlencode(sorted_params)
        x_sign = hmac.new(merchant_key_self_validate.encode("utf-8"), hash_string.encode("utf-8"), hashlib.sha1).hexdigest()

        post_data = urllib.parse.urlencode(data)

        # Проверяем, была ли уже обработана транзакция
        if data.get("transaction_id") in processed_transactions:
            return {
                "balance": 100.0,  # Пример баланса
                "transaction_id": data["transaction_id"]
            }

        # Если транзакция новая, добавляем ее в список обработанных
        processed_transactions.add(data["transaction_id"])

        async with aiohttp.ClientSession() as session:
            async with session.post(url + endpoint, headers={
                **base_headers,
                "X-Sign": x_sign,
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            }, data=post_data) as response:
                result = await response.text()
                print("Response:", result)

                try:
                    return await response.json()
                except Exception as e:
                    print(f"Failed to parse JSON: {e}")
                    return {"error": "Invalid response format"}