import aiohttp
import backoff
from fastapi import HTTPException
import hashlib
import hmac
import time
import uuid

from src.settings import Settings


def generate_headers(params: dict):
    nonce = uuid.uuid4().hex
    timestamp = str(int(time.time()))

    headers = {
        "X-Merchant-Id": Settings.PRAGMATIC_MERCHANT_ID,
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
    }

    merged_params = {**params, **headers}
    sorted_params = sorted(merged_params.items())
    query_string = "&".join(f"{k}={v}" for k, v in sorted_params)
    sign = hmac.new(Settings.PRAGMATIC_MERCHANT_KEY.encode(), query_string.encode(), hashlib.sha1).hexdigest()

    headers["X-Sign"] = sign

    return headers


def handle_response(response):
    if response.status == 200:
        return response.json()
    elif response.status == 201:
        return response.json()
    elif response.status == 204:
        return {"detail": "No content"}
    elif response.status == 304:
        return {"detail": "Not modified"}
    elif response.status == 400:
        raise HTTPException(status_code=400, detail="Bad request")
    elif response.status == 401:
        raise HTTPException(status_code=401, detail="Authentication failed")
    elif response.status == 403:
        raise HTTPException(status_code=403, detail="Forbidden")
    elif response.status == 404:
        raise HTTPException(status_code=404, detail="Resource not found")
    elif response.status == 405:
        raise HTTPException(status_code=405, detail="Method not allowed")
    elif response.status == 415:
        raise HTTPException(status_code=415, detail="Unsupported media type")
    elif response.status == 422:
        raise HTTPException(status_code=422, detail="Data validation failed")
    elif response.status == 429:
        raise HTTPException(status_code=429, detail="Too many requests")
    elif response.status in (430, 500):
        raise HTTPException(status_code=430, detail="Unexpected error")
    else:
        raise HTTPException(status_code=430, detail="Unexpected error")


@backoff.on_exception(backoff.expo, (aiohttp.ClientError, aiohttp.ClientResponseError),
                      max_tries=3,
                      giveup=lambda e: e.status not in [429, 430, 500, 503])
async def make_request(method: str, endpoint: str, params: dict = None, data: dict = None):
    url = f"{Settings.PRAGMATIC_BASE_API_URL}/{endpoint}"
    headers = generate_headers(params or {})

    async with aiohttp.ClientSession() as session:
        if method == "GET":
            async with session.get(url, headers=headers) as response:
                return await handle_response(response)
        elif method == "POST":
            async with session.post(url, headers=headers, data=data) as response:
                return await handle_response(response)
        else:
            raise aiohttp.web.HTTPMethodNotAllowed(method, allowed_methods=["GET", "POST"])
