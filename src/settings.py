import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """List of config variables."""

    HOST_URL = os.environ.get('HOST_URL')

    VK_CLIENT_ID = os.environ.get('VK_CLIENT_ID')
    VK_SECRET_KEY = os.environ.get('VK_SECRET_KEY')
    VK_REDIRECT_URI = os.environ.get('VK_REDIRECT_URI')

    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')

    POSTGRES_USER = os.environ.get('POSTGRES_USER', 'postgres')
    POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD', 'postgres')
    POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "localhost")
    POSTGRES_DB = os.environ.get('POSTGRES_DB', 'postgres')

    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')
    REDIS_PORT = os.environ.get('REDIS_PORT')
    REDIS_DATABASES = os.environ.get('REDIS_DATABASES')

    # Pragmatic
    PRAGMATIC_BASE_API_URL = os.getenv("PRAGMATIC_BASE_API_URL")
    PRAGMATIC_MERCHANT_ID = os.getenv("PRAGMATIC_MERCHANT_ID")
    PRAGMATIC_MERCHANT_KEY = os.getenv("PRAGMATIC_MERCHANT_KEY")