import uvicorn
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from logging_config import setup_logging  # Импортируем настройку логирования

from src.support.route import chat_router, support_router
from src.users.route import router as user_router
from src.wallet.route import router as wallet_router

# providers
from src.providers.pragmatic.route import router as pragmatic_provider_router

# Настройка глобального логирования
setup_logging()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://moon-gamble.vercel.app",
        "https://moon-gamble.fans/"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"]
)

app.include_router(user_router)
app.include_router(wallet_router)
app.include_router(support_router)
app.include_router(chat_router)
app.include_router(pragmatic_provider_router)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
