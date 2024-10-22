import logging
import hmac
import hashlib
import urllib.parse
from fastapi import APIRouter, Request, HTTPException
from decimal import Decimal
from src.wallet.service import TransactionService
from src.providers.pragmatic.utils import make_request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/providers/pragmatic", tags=["Providers", "Pragmatic"])

session_transactions = {}
merchant_id_self_validate = "506866590132dcf90a48f0d66727a3d4"
merchant_key_self_validate = "7b05548b6df95ace55877d34781441174ced8d8e"

users = {}  # Словарь для хранения пользователей по их ID

@router.post("/self-validate")
async def self_validate():
    logger.info("Performing self-validation")
    response = await make_request("POST", "self-validate", data={})
    logger.info("Self-validation completed")
    return response

@router.post("/bet")
async def handle_action(request: Request):
    form_data = await request.form()
    action = form_data.get("action")
    session_id = form_data.get("session_id")

    if not action:
        raise HTTPException(status_code=400, detail="Missing required parameter: 'action'")
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing required parameter: 'session_id'")

    logger.info(f"Received request parameters: {form_data}")

    if session_id not in session_transactions:
        session_transactions[session_id] = []

    transaction_id = form_data.get("transaction_id")

    # Проверяем, существует ли уже транзакция с таким ID в сессии
    if any(tx['id'] == transaction_id for tx in session_transactions[session_id]):
        logger.warning(f"Transaction ID {transaction_id} already processed in session {session_id}")
        return {
            "error_code": "INTERNAL_ERROR",
            "error_description": "Transaction already processed"
        }

    # Сохраняем объект с ID и action
    session_transactions[session_id].append({
        "id": transaction_id,
        "action": action
    })
    logger.info(f"Added transaction {transaction_id} with action '{action}' to session {session_id}")

    signature_ok = await check_signature(request, form_data)
    if not signature_ok:
        logger.error("Invalid signature")
        return {"error_code": "INTERNAL_ERROR", "error_description": "Invalid signature"}

    try:
        if action == "bet":
            return await process_bet(form_data)
        elif action == "win":
            return await process_win(form_data)
        elif action == "refund":
            return await process_refund(form_data)
        elif action == "balance":
            return await process_balance(form_data)
        else:
            logger.error("Unexpected action type")
            return {"error_code": "INTERNAL_ERROR", "error_description": "Unexpected action type"}
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        return {"error_code": "INTERNAL_ERROR", "error_description": "Unexpected server error. Please contact support."}

async def process_bet(form_data):
    required_fields = ["player_id", "amount", "currency", "game_uuid", "transaction_id", "session_id", "type"]
    for field in required_fields:
        if field not in form_data:
            raise HTTPException(status_code=400, detail=f"Missing required parameter: '{field}'")

    user_id = form_data.get("player_id")
    amount = Decimal(form_data.get("amount"))

    if user_id not in users:
        users[user_id] = {"balance": Decimal(0)}  # Создание нового пользователя с нулевым балансом
        logger.info(f"Created user with ID {user_id}")

    if amount == 0:
        return {"balance": float(users[user_id]["balance"]), "transaction_id": form_data.get("transaction_id")}

    if amount < 0:
        logger.warning(f"Bet amount {amount} must be greater than or equal to zero")
        return {"error_code": "INTERNAL_ERROR", "error_description": "Bet amount must be greater than or equal to zero"}

    if users[user_id]["balance"] < amount:
        logger.warning(f"Insufficient funds for player {user_id}: {users[user_id]['balance']} < {amount}")
        return {
            "error_code": "INSUFFICIENT_FUNDS",
            "error_description": "Not enough money to place this bet"
        }

    users[user_id]["balance"] -= amount
    logger.info(f"Processed bet for player {user_id}: {amount}")
    return {"balance": float(users[user_id]["balance"]), "transaction_id": form_data.get("transaction_id")}

async def process_win(form_data):
    required_fields = ["player_id", "amount", "currency", "game_uuid", "transaction_id", "session_id", "type"]
    for field in required_fields:
        if field not in form_data:
            raise HTTPException(status_code=400, detail=f"Missing required parameter: '{field}'")

    user_id = form_data.get("player_id")
    amount = Decimal(form_data.get("amount"))

    if user_id not in users:
        users[user_id] = {"balance": Decimal(0)}
        logger.info(f"Created user with ID {user_id}")

    if amount == 0:
        return {"balance": float(users[user_id]["balance"]), "transaction_id": form_data.get("transaction_id")}

    users[user_id]["balance"] += amount
    logger.info(f"Processed win for player {user_id}: {amount}")
    return {"balance": float(users[user_id]["balance"]), "transaction_id": form_data.get("transaction_id")}

async def process_refund(form_data):
    required_fields = ["player_id", "amount", "currency", "game_uuid", "transaction_id", "session_id", "bet_transaction_id"]
    for field in required_fields:
        if field not in form_data:
            raise HTTPException(status_code=400, detail=f"Missing required parameter: '{field}'")

    user_id = form_data.get("player_id")
    amount = Decimal(form_data.get("amount"))
    bet_transaction_id = form_data.get("bet_transaction_id")

    # Проверяем, существует ли ставка с указанным bet_transaction_id
    bet_transaction = next((tx for tx in session_transactions[form_data.get("session_id")] if tx['id'] == bet_transaction_id), None)

    if bet_transaction and bet_transaction['action'] == 'win':
        logger.warning(f"Cannot refund a winning transaction: {bet_transaction_id}")
        return {
            "error_code": "INTERNAL_ERROR",
            "error_description": "Cannot refund a winning transaction"
        }

    if user_id not in users:
        users[user_id] = {"balance": Decimal(0)}
        logger.info(f"Created user with ID {user_id}")

    if amount == 0:
        return {"balance": float(users[user_id]["balance"]), "transaction_id": form_data.get("transaction_id")}

    users[user_id]["balance"] += amount
    logger.info(f"Processed refund for player {user_id}: {amount}")
    return {"balance": float(users[user_id]["balance"]), "transaction_id": form_data.get("transaction_id")}

async def process_balance(form_data):
    required_fields = ["player_id", "currency"]
    for field in required_fields:
        if field not in form_data:
            raise HTTPException(status_code=400, detail=f"Missing required parameter: '{field}'")

    user_id = form_data.get("player_id")

    if user_id not in users:
        users[user_id] = {"balance": Decimal(0)}
        logger.info(f"Created user with ID {user_id}")

    logger.info(f"Retrieved balance for player {user_id}: {users[user_id]['balance']}")
    return {"balance": float(users[user_id]["balance"]), "transaction_id": "N/A"}

async def check_signature(request: Request, form_data: dict):
    headers = request.headers
    merchant_key = merchant_key_self_validate

    x_merchant_id = headers.get("X-Merchant-Id")
    x_timestamp = headers.get("X-Timestamp")
    x_nonce = headers.get("X-Nonce")
    x_sign = headers.get("X-Sign")

    if not (x_merchant_id and x_timestamp and x_nonce and x_sign):
        return False

    combined_params = {**form_data, "X-Merchant-Id": x_merchant_id, "X-Timestamp": x_timestamp, "X-Nonce": x_nonce}
    sorted_params = dict(sorted(combined_params.items()))
    hash_string = urllib.parse.urlencode(sorted_params)
    calculated_sign = hmac.new(merchant_key.encode("utf-8"), hash_string.encode("utf-8"), hashlib.sha1).hexdigest()

    return calculated_sign == x_sign
