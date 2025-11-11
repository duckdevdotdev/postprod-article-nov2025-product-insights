import json
import requests
import logging
from typing import Dict, Any, Optional
from config import LLM_CONFIG

logger = logging.getLogger(__name__)


class LLMProcessor:
    def __init__(self, provider="yandex"):
        self.provider = provider
        self.config = LLM_CONFIG.get(provider, {})

    def analyze_call(self, call_text: str) -> Optional[Dict[str, Any]]:
        try:
            if self.provider == "yandex":
                return self._call_yandex_gpt(call_text)
            else:
                return self._fallback_analysis(call_text)
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return None

    def _call_yandex_gpt(self, call_text: str) -> Dict[str, Any]:
        from prompts import get_analysis_prompt

        url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        headers = {
            "Authorization": f"Api-Key {self.config['api_key']}",
            "Content-Type": "application/json"
        }

        prompt = get_analysis_prompt(call_text)

        data = {
            "modelUri": f"gpt://{self.config['folder_id']}/{self.config['model']}",
            "completionOptions": {
                "stream": False,
                "temperature": self.config["temperature"],
                "maxTokens": self.config["max_tokens"]
            },
            "messages": [
                {
                    "role": "system",
                    "text": "Ты — маркетолог-аналитик, который анализирует звонки с клиентами."
                },
                {
                    "role": "user",
                    "text": prompt
                }
            ]
        }

        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()

        result = response.json()
        response_text = result["result"]["alternatives"][0]["message"]["text"]

        try:
            return json.loads(response_text.strip())
        except json.JSONDecodeError:
            return self._fallback_analysis(response_text)

    # В llm_utils.py нужно обновить метод _fallback_analysis:
    def _fallback_analysis(text: str) -> Dict[str, Any]:
        return {
            "main_problem": "Не удалось определить проблему",
            "key_fear": "Не удалось определить страх",
            "result_solution": "Не удалось определить желаемый результат",
            "original_phrases": ["Не удалось извлечь цитаты"],
            "tags": ["неопределено"]
        }

    def generate_creatives(self, analysis_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            from prompts import get_creatives_prompt

            if self.provider == "yandex":
                return self._generate_with_yandex(analysis_data)
            else:
                return self._generate_fallback_creatives(analysis_data)
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return None

    def _generate_with_yandex(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        from prompts import get_creatives_prompt

        url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        headers = {
            "Authorization": f"Api-Key {self.config['api_key']}",
            "Content-Type": "application/json"
        }

        prompt = get_creatives_prompt(analysis_data)

        data = {
            "modelUri": f"gpt://{self.config['folder_id']}/{self.config['model']}",
            "completionOptions": {
                "stream": False,
                "temperature": 0.7,
                "maxTokens": self.config["max_tokens"]
            },
            "messages": [
                {
                    "role": "system",
                    "text": "Ты — копирайтер для рекламных объявлений."
                },
                {
                    "role": "user",
                    "text": prompt
                }
            ]
        }

        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()

        result = response.json()
        response_text = result["result"]["alternatives"][0]["message"]["text"]

        try:
            return json.loads(response_text.strip())
        except json.JSONDecodeError:
            return self._generate_fallback_creatives(analysis_data)

    def _generate_fallback_creatives(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        main_problem = analysis_data.get("main_problem", "проблема")
        phrases = analysis_data.get("original_phrases", [""])

        return {
            "headlines": [
                f"Решаем {main_problem.lower()}",
                f"Больше нет {main_problem.lower()}",
                phrases[0] if phrases else f"Решение для {main_problem.lower()}"
            ],
            "ad_texts": [
                f"Избавляем от {main_problem.lower()}. Проверенное решение.",
                f"Клиенты говорят: '{phrases[0]}'. Мы знаем как помочь."
            ]
        }


def analyze_call_with_llm(call_text: str, provider: str = "yandex") -> Optional[Dict[str, Any]]:
    processor = LLMProcessor(provider)
    return processor.analyze_call(call_text)


def generate_creatives(analysis_data: Dict[str, Any], provider: str = "yandex") -> Optional[Dict[str, Any]]:
    processor = LLMProcessor(provider)
    return processor.generate_creatives(analysis_data)
