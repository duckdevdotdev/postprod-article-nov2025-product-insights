import requests
import logging
from datetime import datetime, timedelta
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
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours_back)

            params = {
                "start_date": start_time.isoformat(),
                "end_date": end_time.isoformat(),
                "limit": 50
            }

            response = requests.get(
                "https://app.exolve.ru/api/v1/statistics/calls",
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
        """Получает транскрипцию звонка через POST /GetTranscribation"""
        try:
            logger.info(f"Получение расшифровки для звонка {call_id}")

            # POST запрос к endpoint GetTranscribation
            transcript_url = f"{self.base_url}/GetTranscribation"

            # Тело запроса с ID звонка
            payload = {
                "call_id": call_id
            }

            # Выполняем POST-запрос к API Exolve
            response = requests.post(
                transcript_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                transcript_data = response.json()
                transcript_text = self._extract_transcript_from_response(transcript_data)

                if transcript_text:
                    logger.info(f"Получена расшифровка: {len(transcript_text)} символов")
                    return transcript_text
                else:
                    logger.warning(f"Пустая расшифровка для звонка {call_id}")
                    return None
            else:
                logger.error(f"API Error: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Ошибка получения расшифровки: {e}")
            return None

    def _extract_transcript_from_response(self, transcript_data: Dict) -> str:
        """Извлекает текст транскрипции из ответа API GetTranscribation"""
        try:
            # Анализируем структуру ответа
            logger.info(f"Структура ответа: {list(transcript_data.keys())}")

            # Пробуем разные возможные структуры ответа
            possible_paths = [
                ["text"],
                ["transcript"],
                ["transcription"],
                ["result", "text"],
                ["data", "text"],
                ["call", "transcript"],
                ["TranscribationText"],  # Возможное поле для текста транскрипции
                ["TranscriptionText"],
                ["Text"]
            ]

            for path in possible_paths:
                current = transcript_data
                try:
                    for key in path:
                        current = current[key]
                    if current and isinstance(current, str):
                        logger.info(f"Транскрипция найдена по пути: {path}")
                        return current.strip()
                except (KeyError, TypeError):
                    continue

            # Если это список фраз/сегментов
            if isinstance(transcript_data, list):
                phrases = []
                for item in transcript_data:
                    if isinstance(item, dict) and item.get("text"):
                        phrases.append(item["text"])
                    elif isinstance(item, str):
                        phrases.append(item)
                if phrases:
                    return " ".join(phrases)

            # Сохраняем полный ответ для отладки
            with open("transcribation_debug.json", "w", encoding="utf-8") as f:
                import json
                json.dump(transcript_data, f, ensure_ascii=False, indent=2)

            logger.warning(f"Не удалось извлечь транскрипцию. Полный ответ сохранен в transcribation_debug.json")
            return ""

        except Exception as e:
            logger.error(f"Ошибка извлечения транскрипции: {e}")
            return ""

    def get_call_details(self, call_id: str) -> Optional[Dict]:
        """Получает детальную информацию о звонке"""
        try:
            response = requests.get(
                f"https://app.exolve.ru/api/v1/statistics/calls/{call_id}",
                headers=self.headers,
                timeout=30
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API Error: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error: {e}")
            return None

    def test_api_connection(self) -> bool:
        """Тестирует подключение к API"""
        try:
            response = requests.get(
                "https://app.exolve.ru/api/v1/statistics/calls",
                headers=self.headers,
                params={"limit": 1},
                timeout=10
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"API connection test failed: {e}")
            return False

    def get_available_transcripts(self, hours_back: int = 24) -> List[Dict]:
        """Получает список звонков с доступными транскрипциями"""
        calls = self.get_recent_calls(hours_back)
        calls_with_transcripts = []

        for call in calls:
            call_id = call.get("id")
            if call_id:
                transcript = self.get_call_transcript(call_id)
                if transcript and len(transcript) > 50:  # Минимум 50 символов
                    calls_with_transcripts.append({
                        "call_id": call_id,
                        "transcript_length": len(transcript),
                        "preview": transcript[:100] + "..." if len(transcript) > 100 else transcript,
                        "call_data": call
                    })

        return calls_with_transcripts


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
