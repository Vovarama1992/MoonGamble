import logging
from fastapi import APIRouter, Request, HTTPException, FastAPI
from decimal import Decimal
from src.providers.pragmatic.utils import make_request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/providers/pragmatic", tags=["Providers", "Pragmatic"])

# Данные для валидации
merchant_id_self_validate = "506866590132dcf90a48f0d66727a3d4"
merchant_key_self_validate = "7b05548b6df95ace55877d34781441174ced8d8e"

# Статусы пользователей и сессий
users = {"1": {"balance": Decimal("0.00"), "bets": [], "wins": [], "refunds": []}}
session_transactions = {}

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
    transaction_id = form_data.get("transaction_id")
    player_id = form_data.get("player_id")

    # Проверка наличия session_id, transaction_id, player_id
    if not session_id or not transaction_id or not player_id:
        logger.error("Missing session_id, transaction_id, or player_id in the request")
        return {"error_code": "INTERNAL_ERROR", "error_description": "Invalid session or transaction data"}

    logger.info(f"Handling action '{action}' for session_id '{session_id}', player_id '{player_id}', transaction_id '{transaction_id}'")

    validate_required_fields(form_data, ["action", "session_id", "transaction_id", "player_id"])

    # Проверка существующего игрока
    if player_id not in users:
        logger.error(f"Player with player_id '{player_id}' not found")
        return {"error_code": "INTERNAL_ERROR", "error_description": "Player not found"}

    # Проверка привязки сессии к игроку
    if session_id not in session_transactions:
        session_transactions[session_id] = {"transactions": [], "player_id": player_id}
        logger.info(f"New session created for player_id '{player_id}' with session_id '{session_id}'")
    elif session_transactions[session_id]["player_id"] != player_id:
        logger.error(f"Session '{session_id}' is tied to a different player")
        return {"error_code": "INTERNAL_ERROR", "error_description": "Session is tied to a different player"}

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
            logger.error(f"Unexpected action type '{action}' for session_id '{session_id}'")
            return {"error_code": "INTERNAL_ERROR", "error_description": "Unexpected action type"}
    except Exception as e:
        logger.error(f"Unhandled exception for session_id '{session_id}': {e}")
        return {"error_code": "INTERNAL_ERROR", "error_description": "Unexpected server error. Please contact support."}

def validate_required_fields(form_data, required_fields):
    for field in required_fields:
        if field not in form_data:
            raise HTTPException(status_code=400, detail=f"Missing required parameter: '{field}'")

async def process_bet(form_data):
    player_id = form_data.get("player_id")
    transaction_id = form_data.get("transaction_id")
    amount = Decimal(form_data.get("amount", "0.00"))
    session_id = form_data.get("session_id")

    logger.info(f"Processing bet for session_id '{session_id}', transaction_id '{transaction_id}', amount '{amount}'")

    if any(bet["transaction_id"] == transaction_id for bet in users[player_id].get("bets", [])):
        logger.info(f"Duplicate transaction detected for transaction_id '{transaction_id}' in session_id '{session_id}'")
        return {
            "balance": float(users[player_id]["balance"]),
            "transaction_id": transaction_id
        }

    if amount == Decimal("0.00"):
        logger.info(f"Received zero amount bet for session_id '{session_id}', returning balance and transaction ID without changes.")
        users[player_id].setdefault("bets", []).append({"transaction_id": transaction_id, "amount": amount})
        return {
            "balance": float(users[player_id]["balance"]),
            "transaction_id": transaction_id
        }

    if users[player_id]["balance"] < amount:
        logger.warning(f"Insufficient funds for bet in session_id '{session_id}', player_id '{player_id}'")
        return {"error_code": "INSUFFICIENT_FUNDS", "error_description": "Not enough money to place this bet"}

    users[player_id]["balance"] -= amount
    users[player_id].setdefault("bets", []).append({"transaction_id": transaction_id, "amount": amount})
    return {
        "balance": float(users[player_id]["balance"]),
        "transaction_id": transaction_id
    }

async def process_win(form_data):
    player_id = form_data.get("player_id")
    transaction_id = form_data.get("transaction_id")
    amount = Decimal(form_data.get("amount", "0.00"))
    bet_transaction_id = form_data.get("bet_transaction_id")

    logger.info(f"Processing win for player_id '{player_id}', transaction_id '{transaction_id}', amount '{amount}', bet_transaction_id '{bet_transaction_id}'")

    if any(bet["transaction_id"] == bet_transaction_id and bet["amount"] == Decimal("0.00") for bet in users[player_id].get("bets", [])):
        logger.error("Attempted win on a zero amount bet")
        return {"error_code": "INTERNAL_ERROR", "error_description": "Cannot process win on a zero amount bet"}

    users[player_id]["balance"] += amount
    users[player_id].setdefault("wins", []).append({"transaction_id": transaction_id, "amount": amount})
    return {
        "balance": float(users[player_id]["balance"]),
        "transaction_id": transaction_id
    }

async def process_refund(form_data):
    player_id = form_data.get("player_id")
    transaction_id = form_data.get("transaction_id")
    amount = Decimal(form_data.get("amount", "0.00"))
    bet_transaction_id = form_data.get("bet_transaction_id")

    logger.info(f"Processing refund for player_id '{player_id}', transaction_id '{transaction_id}', amount '{amount}', bet_transaction_id '{bet_transaction_id}'")

    if any(bet["transaction_id"] == bet_transaction_id and bet["amount"] == Decimal("0.00") for bet in users[player_id].get("bets", [])):
        logger.error("Attempted refund on a zero amount bet")
        return {"error_code": "INTERNAL_ERROR", "error_description": "Cannot process refund on a zero amount bet"}

    users[player_id]["balance"] += amount
    users[player_id].setdefault("refunds", []).append({"transaction_id": transaction_id, "amount": amount})
    return {
        "balance": float(users[player_id]["balance"]),
        "transaction_id": transaction_id
    }

async def process_balance(form_data):
    player_id = form_data.get("player_id")
    logger.info(f"Fetching balance for player_id '{player_id}'")
    return {"balance": float(users[player_id]["balance"])}

app = FastAPI()
app.include_router(router)