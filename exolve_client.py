import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os

logger = logging.getLogger(__name__)


class ExolveClient:
    def __init__(self):
        self.api_key = os.getenv("EXOLVE_API_KEY")
        self.base_url = "https://app.exolve.ru/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def get_recent_calls(self, hours_back: int = 1) -> List[Dict]:
        try:
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours_back)

            params = {
                "start_date": start_time.isoformat(),
                "end_date": end_time.isoformat(),
                "limit": 50
            }

            response = requests.get(
                f"{self.base_url}/statistics/calls",
                headers=self.headers,
                params=params,
                timeout=30
            )

            if response.status_code == 200:
                return response.json().get("calls", [])
            else:
                logger.error(f"API Error: {response.status_code} - {response.text}")
                return []

        except Exception as e:
            logger.error(f"Error: {e}")
            return []

    def get_call_transcript(self, call_id: str) -> Optional[str]:
        try:
            # Получение деталей звонка с расшифровкой
            call_details_url = f"{self.base_url}/statistics/calls/{call_id}"

            response = requests.get(call_details_url, headers=self.headers, timeout=30)

            if response.status_code == 200:
                call_data = response.json()
                return self._extract_transcript(call_data)
            else:
                logger.error(f"API Error for call {call_id}: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error getting transcript for call {call_id}: {e}")
            return None

    def _extract_transcript(self, call_data: Dict) -> str:
        """Извлекает расшифровку из данных звонка"""
        # Попробуем разные возможные пути к расшифровке
        transcript_paths = [
            ["transcript"],
            ["speech_analytics", "transcript"],
            ["phrases"],
            ["call_details", "transcript"],
            ["result", "transcript"]
        ]

        for path in transcript_paths:
            current = call_data
            try:
                for key in path:
                    current = current[key]
                if current:
                    if isinstance(current, list):
                        return " ".join([phrase.get("text", "") for phrase in current if phrase.get("text")])
                    elif isinstance(current, str):
                        return current
            except (KeyError, TypeError):
                continue

        # Если не нашли структурированную расшифровку, попробуем найти текстовые поля
        transcript_text = self._find_text_fields(call_data)
        if transcript_text:
            return transcript_text

        logger.warning(f"No transcript found in call data. Available keys: {list(call_data.keys())}")
        return ""

    def _find_text_fields(self, data, depth=0, max_depth=3):
        """Рекурсивно ищет текстовые поля в данных"""
        if depth > max_depth:
            return ""

        transcript_parts = []

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str) and len(value) > 50:  # Длинные текстовые поля
                    if any(word in key.lower() for word in ['transcript', 'text', 'phrase', 'speech']):
                        transcript_parts.append(value)
                elif isinstance(value, (dict, list)):
                    found = self._find_text_fields(value, depth + 1, max_depth)
                    if found:
                        transcript_parts.append(found)

        elif isinstance(data, list):
            for item in data:
                found = self._find_text_fields(item, depth + 1, max_depth)
                if found:
                    transcript_parts.append(found)

        return " ".join(transcript_parts) if transcript_parts else ""

    def get_call_details(self, call_id: str) -> Optional[Dict]:
        """Получает полную информацию о звонке для отладки"""
        try:
            call_details_url = f"{self.base_url}/statistics/calls/{call_id}"
            response = requests.get(call_details_url, headers=self.headers, timeout=30)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API Error: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error: {e}")
            return None


class ExolveWebhookProcessor:
    def __init__(self, sheets_manager, llm_processor):
        self.sheets_manager = sheets_manager
        self.llm_processor = llm_processor
        self.processed_calls = set()

    def process_webhook_event(self, event_data: Dict) -> bool:
        try:
            event_type = event_data.get("event_type")
            call_id = event_data.get("call_id")

            if event_type == "call_finished" and call_id and call_id not in self.processed_calls:
                client = ExolveClient()
                transcript = client.get_call_transcript(call_id)

                if transcript and len(transcript) > 50:
                    analysis = self.llm_processor.analyze_call(transcript)
                    if analysis:
                        creatives = self.llm_processor.generate_creatives(analysis)
                        success = self.sheets_manager.append_analysis(
                            os.getenv("GOOGLE_SHEETS_URL"),
                            analysis,
                            creatives
                        )
                        if success:
                            self.processed_calls.add(call_id)
                            return True
            return False

        except Exception as e:
            logger.error(f"Error: {e}")
            return False
