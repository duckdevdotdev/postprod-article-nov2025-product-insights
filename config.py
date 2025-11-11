import os
from dotenv import load_dotenv

load_dotenv()

LLM_CONFIG = {
    "yandex": {
        "api_key": os.getenv("YANDEX_API_KEY"),
        "folder_id": os.getenv("YANDEX_FOLDER_ID"),
        "model": "yandexgpt-lite",
        "temperature": 0.3,
        "max_tokens": 2000
    }
}

SHEETS_CONFIG = {
    "credentials_file": "service_account.json.example",
    "scope": ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
}