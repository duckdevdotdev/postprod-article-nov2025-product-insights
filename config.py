import os
from dotenv import load_dotenv

load_dotenv()

LLM_CONFIG = {
    "yandex": {
        "api_key": os.getenv("YANDEX_API_KEY"),
        "folder_id": os.getenv("YANDEX_FOLDER_ID"),
        "model": os.getenv("YANDEX_MODEL", "yandexgpt-lite"),
        "temperature": float(os.getenv("YANDEX_TEMPERATURE", "0.3")),
        "max_tokens": int(os.getenv("YANDEX_MAX_TOKENS", "2000")),
    }
}
