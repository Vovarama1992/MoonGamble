import requests
import hashlib
import time
import hmac
import urllib.parse
import random
import uuid

url = 'https://staging.gamerouter.pw/api/index.php/v1/games/init'

merchant_id = '506866590132dcf90a48f0d66727a3d4'
merchant_key = '7b05548b6df95ace55877d34781441174ced8d8e'

current_time = str(int(time.time()))
nonce = hashlib.md5(str(uuid.uuid4()).encode('utf-8')).hexdigest()

headers = {
    'X-Merchant-Id': merchant_id,
    'X-Timestamp': current_time,
    'X-Nonce': nonce,
}

request_params = {
    'player_name': 'qqq',
    'game_uuid': '23ca989db9ca5ad94dbca17fa54a123f3f7efc9d',
    'player_id': '1',
    'currency': 'EUR',
    'session_id': 'session-{}'.format(current_time),
}

merged_params = {**request_params, **headers}
sorted_params = dict(sorted(merged_params.items()))
hash_string = urllib.parse.urlencode(sorted_params)


x_sign = hmac.new(merchant_key.encode('utf-8'), hash_string.encode('utf-8'), hashlib.sha1).hexdigest()

sorted_request_params = dict(sorted(request_params.items()))
post_data = urllib.parse.urlencode(sorted_request_params)

response = requests.post(url, headers={
    'X-Merchant-Id': merchant_id,
    'X-Timestamp': current_time,
    'X-Nonce': nonce,
    'X-Sign': x_sign,
    'Accept': 'application/json',
    'Content-Type': 'application/x-www-form-urlencoded',
}, data=post_data)

print("Merged Params:", merged_params)
print("Sorted and Encoded Params (for hash):", hash_string)
print("Post Data:", post_data)
print("X-Sign:", x_sign)
print("Response:", response.text)