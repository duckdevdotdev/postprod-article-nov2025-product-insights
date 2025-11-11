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
            logger.error(f"Ошибка анализа звонка: {e}")
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
                    "text": "Ты — продуктовый аналитик, который анализирует обращения клиентов."
                },
                {
                    "role": "user",
                    "text": prompt
                }
            ]
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()

            result = response.json()
            response_text = result["result"]["alternatives"][0]["message"]["text"]

            try:
                return json.loads(response_text.strip())
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка парсинга JSON: {e}")
                logger.info(f"Ответ от API: {response_text}")
                return self._fallback_analysis(response_text)

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка запроса к Yandex GPT: {e}")
            return self._fallback_analysis(call_text)

    def _fallback_analysis(self, text: str) -> Dict[str, Any]:
        """Фолбек анализ когда основной не сработал"""
        return {
            "main_problem": "Не удалось определить проблему",
            "key_fear": "Не удалось определить страх",
            "result_solution": "Не удалось определить желаемый результат",
            "original_phrases": ["Не удалось извлечь цитаты"],
            "tags": ["неопределено"]
        }

    def generate_product_insights(self, analysis_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            if self.provider == "yandex":
                return self._generate_insights_with_yandex(analysis_data)
            else:
                return self._generate_fallback_insights(analysis_data)
        except Exception as e:
            logger.error(f"Ошибка генерации инсайтов: {e}")
            return None

    def _generate_insights_with_yandex(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        from prompts import get_product_insights_prompt

        url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        headers = {
            "Authorization": f"Api-Key {self.config['api_key']}",
            "Content-Type": "application/json"
        }

        prompt = get_product_insights_prompt(analysis_data)

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
                    "text": "Ты — продуктовый аналитик, который анализирует клиентские обращения для улучшения продукта."
                },
                {
                    "role": "user",
                    "text": prompt
                }
            ]
        }

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()

            result = response.json()
            response_text = result["result"]["alternatives"][0]["message"]["text"]

            try:
                return json.loads(response_text.strip())
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка парсинга JSON инсайтов: {e}")
                logger.info(f"Ответ от API: {response_text}")
                return self._generate_fallback_insights(analysis_data)

        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка запроса для генерации инсайтов: {e}")
            return self._generate_fallback_insights(analysis_data)

    def _generate_fallback_insights(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Фолбек инсайты когда основной запрос не сработал"""
        main_problem = analysis_data.get("main_problem", "проблема")
        key_fear = analysis_data.get("key_fear", "страх")
        result_solution = analysis_data.get("result_solution", "решение")

        return {
            "product_insights": [
                f"Клиенты сталкиваются с {main_problem.lower()}, что вызывает {key_fear.lower()}",
                f"Пользователи хотят достичь: {result_solution.lower()}",
                "Необходимо упростить процесс решения данной проблемы"
            ],
            "feature_suggestions": [
                f"Добавить функцию для решения {main_problem.lower()}",
                "Реализовать уведомления о статусе операций",
                "Создать справочный раздел по частым проблемам"
            ],
            "ux_improvements": [
                "Упростить навигацию в проблемной области",
                "Добавить подсказки и инструкции для новых пользователей",
                "Улучшить обратную связь о выполнении операций"
            ],
            "priority_level": "medium"
        }


def analyze_call_with_llm(call_text: str, provider: str = "yandex") -> Optional[Dict[str, Any]]:
    processor = LLMProcessor(provider)
    return processor.analyze_call(call_text)


def generate_product_insights(analysis_data: Dict[str, Any], provider: str = "yandex") -> Optional[Dict[str, Any]]:
    processor = LLMProcessor(provider)
    return processor.generate_product_insights(analysis_data)
