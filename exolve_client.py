import requests
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import os

logger = logging.getLogger(__name__)


class ExolveClient:
    def __init__(self):
        self.api_key = os.getenv("EXOLVE_API_KEY")
        self.base_url = "https://api.exolve.ru/statistics/call-record/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def get_recent_calls(self, hours_back: int = 1) -> List[Dict]:
        """Получает список последних звонков"""
        try:
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=hours_back)

            url = "https://api.exolve.ru/statistics/call-history/v2/GetList"
            payload = {
                "date_from": start_time.isoformat().replace("+00:00", "Z"),
                "date_to": end_time.isoformat().replace("+00:00", "Z"),
                "limit": 50,
                "offset": 0
            }

            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()

            data = response.json()
            return data.get("calls") or data.get("list") or []

        except requests.exceptions.RequestException as e:
            logger.error(f"API Error: {e}")
            return []

    def get_call_transcript(self, call_uid: int) -> Optional[str]:
        """Получает транскрипцию звонка через POST /GetTranscribation"""
        try:
            logger.info(f"Получение расшифровки для звонка {call_uid}")

            url = "https://api.exolve.ru/statistics/call-record/v1/GetTranscribation"
            payload = {"uid": int(call_uid)}

            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()

            resp = response.json()
            items = resp.get("transcribation") or []
            if not items:
                logger.warning(f"Транскрипция для звонка {call_uid} не найдена.")
                return None

            item = items[0]
            chunks = item.get("chunks")
            if isinstance(chunks, dict):
                chunks = [chunks]

            phrases = []
            for ch in (chunks or []):
                text = (ch.get("text") or "").strip()
                if text:
                    phrases.append(text)

            transcript_text = " ".join(phrases) if phrases else None
            if transcript_text:
                logger.info(f"Получена расшифровка для звонка {call_uid}: {len(transcript_text)} символов")
                return transcript_text
            else:
                logger.warning(f"Пустая расшифровка для звонка {call_uid}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка получения транскрипции для звонка {call_uid}: {e}")
            return None

    def get_call_details(self, call_uid: int) -> Optional[Dict]:
        """Получает детальную информацию о звонке"""
        try:
            url = "https://api.exolve.ru/statistics/call-history/v2/GetInfo"
            payload = {"uid": int(call_uid)}

            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка получения деталей звонка {call_uid}: {e}")
            return None

    def test_api_connection(self) -> bool:
        """Тестирует подключение к API"""
        try:
            response = requests.get(
                "https://api.exolve.ru/statistics/call-history/v2/GetList",
                headers=self.headers,
                params={"limit": 1},
                timeout=10
            )
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            logger.error(f"API connection test failed: {e}")
            return False

    def get_available_transcripts(self, hours_back: int = 24) -> List[Dict]:
        """Получает список звонков с доступными транскрипциями"""
        calls = self.get_recent_calls(hours_back)
        calls_with_transcripts = []

        for call in calls:
            call_uid = call.get("uid")
            if call_uid:
                transcript = self.get_call_transcript(call_uid)
                if transcript and len(transcript) > 50:  # Минимум 50 символов
                    calls_with_transcripts.append({
                        "call_uid": call_uid,
                        "transcript_length": len(transcript),
                        "preview": transcript[:100] + "..." if len(transcript) > 100 else transcript,
                        "call_data": call
                    })

        return calls_with_transcripts
