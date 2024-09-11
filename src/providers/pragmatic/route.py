import logging

from fastapi import APIRouter, Depends

from src.providers.dependencies import get_current_active_user
from src.providers.schemas import SelfValidateResponse, ReadProfile
from src.providers.pragmatic.utils import make_request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/providers/pragmatic",
                   tags=["Providers", "Pragmatic"])


@router.get("/games")
async def get_games(user: ReadProfile = Depends(get_current_active_user)):
    return await make_request("GET", "games")


@router.get("/games/lobby")
async def get_lobby(game_uuid: str, currency: str, user: ReadProfile = Depends(get_current_active_user)):
    params = {"game_uuid": game_uuid, "currency": currency}
    return await make_request("GET", "games/lobby", params)


@router.post("/games/init")
async def init_game_session(
    data: dict,
    user: ReadProfile = Depends(get_current_active_user)
):
    game_uuid = data.get("game_uuid")
    player_id = data.get("player_id")
    player_name = data.get("player_name")
    currency = data.get("currency")
    session_id = data.get("session_id")
    return_url = data.get("return_url", None)
    language = data.get("language", None)
    lobby_data = data.get("lobby_data", None)

    if not game_uuid or not player_id or not player_name or not currency or not session_id:
        raise HTTPException(status_code=400, detail="Missing required fields")

    game_data = {
        "game_uuid": game_uuid,
        "player_id": player_id,
        "player_name": player_name,
        "currency": currency,
        "session_id": session_id,
        "return_url": return_url,
        "language": language,
        "lobby_data": lobby_data,
    }

    return await make_request("POST", "games/init", data=game_data)


@router.post("/balance")
async def balance_request(player_id: str, currency: str, session_id: str = None,
                          user: ReadProfile = Depends(get_current_active_user)):
    data = {"action": "balance", "player_id": player_id, "currency": currency, "session_id": session_id}
    return await make_request("POST", "balance", data=data)


@router.post("/bet")
async def bet_request(player_id: str, game_uuid: str, amount: float, currency: str, transaction_id: str,
                      session_id: str, bet_type: str = "bet", user: ReadProfile = Depends(get_current_active_user)):
    data = {
        "action": "bet",
        "player_id": player_id,
        "game_uuid": game_uuid,
        "amount": amount,
        "currency": currency,
        "transaction_id": transaction_id,
        "session_id": session_id,
        "type": bet_type,
    }
    return await make_request("POST", "bet", data=data)


@router.post("/win")
async def win_request(player_id: str, game_uuid: str, amount: float, currency: str, transaction_id: str,
                      session_id: str, win_type: str = "win", user: ReadProfile = Depends(get_current_active_user)):
    data = {
        "action": "win",
        "player_id": player_id,
        "game_uuid": game_uuid,
        "amount": amount,
        "currency": currency,
        "transaction_id": transaction_id,
        "session_id": session_id,
        "type": win_type,
    }
    return await make_request("POST", "win", data=data)


@router.post("/refund")
async def refund_request(player_id: str, game_uuid: str, amount: float, currency: str, transaction_id: str,
                         session_id: str, bet_transaction_id: str,
                         user: ReadProfile = Depends(get_current_active_user)):
    data = {
        "action": "refund",
        "player_id": player_id,
        "game_uuid": game_uuid,
        "amount": amount,
        "currency": currency,
        "transaction_id": transaction_id,
        "session_id": session_id,
        "bet_transaction_id": bet_transaction_id,
    }
    return await make_request("POST", "refund", data=data)


@router.post("/rollback")
async def rollback_request(player_id: str, game_uuid: str, currency: str, transaction_id: str,
                           rollback_transactions: list, user: ReadProfile = Depends(get_current_active_user)):
    data = {
        "action": "rollback",
        "player_id": player_id,
        "game_uuid": game_uuid,
        "currency": currency,
        "transaction_id": transaction_id,
        "rollback_transactions": rollback_transactions,
    }
    return await make_request("POST", "rollback", data=data)


@router.get("/limits")
async def get_limits(user: ReadProfile = Depends(get_current_active_user)):
    return await make_request("GET", "limits")


@router.get("/limits/freespin")
async def get_freespin_limits(user: ReadProfile = Depends(get_current_active_user)):
    return await make_request("GET", "limits/freespin")


@router.get("/jackpots")
async def get_jackpots(user: ReadProfile = Depends(get_current_active_user)):
    return await make_request("GET", "jackpots")


@router.post("/balance/notify")
async def notify_balance_change(balance: float, session_id: str, user: ReadProfile = Depends(get_current_active_user)):
    data = {
        "balance": balance,
        "session_id": session_id
    }
    return await make_request("POST", "balance/notify", data=data)


@router.get("/freespins/bets")
async def get_freespin_bets(game_uuid: str, currency: str, user: ReadProfile = Depends(get_current_active_user)):
    params = {"game_uuid": game_uuid, "currency": currency}
    return await make_request("GET", "freespins/bets", params)


@router.post("/freespins/set")
async def set_freespin_campaign(player_id: str, player_name: str, currency: str, quantity: int, valid_from: int,
                                valid_until: int, game_uuid: str, freespin_id: str, bet_id: int = None,
                                total_bet_id: int = None, denomination: float = None,
                                user: ReadProfile = Depends(get_current_active_user)):
    data = {
        "player_id": player_id,
        "player_name": player_name,
        "currency": currency,
        "quantity": quantity,
        "valid_from": valid_from,
        "valid_until": valid_until,
        "game_uuid": game_uuid,
        "freespin_id": freespin_id,
        "bet_id": bet_id,
        "total_bet_id": total_bet_id,
        "denomination": denomination
    }
    return await make_request("POST", "freespins/set", data=data)


@router.get("/freespins/get")
async def get_freespin_campaign(freespin_id: str, user: ReadProfile = Depends(get_current_active_user)):
    params = {"freespin_id": freespin_id}
    return await make_request("GET", "freespins/get", params)


@router.post("/freespins/cancel")
async def cancel_freespin_campaign(freespin_id: str, user: ReadProfile = Depends(get_current_active_user)):
    data = {"freespin_id": freespin_id}
    return await make_request("POST", "freespins/cancel", data=data)


@router.post("/self-validate", response_model=SelfValidateResponse)
async def self_validate():
    return await make_request("POST", "self-validate")



