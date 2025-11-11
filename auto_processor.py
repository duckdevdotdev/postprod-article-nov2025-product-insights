import time
import schedule
import logging
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

from exolve_client import ExolveClient
from llm_utils import LLMProcessor
from sheet_utils import GoogleSheetsManager

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AutoCallProcessor:
    def __init__(self):
        self.exolve_client = ExolveClient()
        self.llm_processor = LLMProcessor()
        self.sheets_manager = GoogleSheetsManager()
        self.processed_call_ids = set()
        self.load_processed_calls()

    def load_processed_calls(self):
        try:
            if os.path.exists('processed_calls.txt'):
                with open('processed_calls.txt', 'r') as f:
                    self.processed_call_ids = set(line.strip() for line in f)
            logger.info(f"Загружено {len(self.processed_call_ids)} обработанных звонков")
        except Exception as e:
            logger.error(f"Ошибка загрузки processed_calls: {e}")

    def save_processed_calls(self):
        try:
            with open('processed_calls.txt', 'w') as f:
                for call_id in self.processed_call_ids:
                    f.write(f"{call_id}\n")
        except Exception as e:
            logger.error(f"Ошибка сохранения processed_calls: {e}")

    def process_new_calls(self):
        try:
            logger.info("Проверка новых звонков...")
            recent_calls = self.exolve_client.get_recent_calls(hours_back=1)
            logger.info(f"Найдено звонков: {len(recent_calls)}")

            new_processed = 0
            for call in recent_calls:
                call_id = call.get("id")
                if not call_id or call_id in self.processed_call_ids:
                    continue

                logger.info(f"Обработка нового звонка: {call_id}")
                transcript = self.exolve_client.get_call_transcript(call_id)

                if transcript and len(transcript) > 100:
                    logger.info(f"Транскрипция получена: {len(transcript)} символов")

                    analysis = self.llm_processor.analyze_call(transcript)
                    if analysis:
                        # Проверяем наличие метода generate_product_insights
                        if hasattr(self.llm_processor, 'generate_product_insights'):
                            insights = self.llm_processor.generate_product_insights(analysis)

                            if insights:
                                success = self.sheets_manager.append_analysis(
                                    os.getenv("GOOGLE_SHEETS_URL"),
                                    analysis,
                                    insights
                                )
                                if success:
                                    self.processed_call_ids.add(call_id)
                                    new_processed += 1
                                    logger.info(f"Звонок {call_id} успешно обработан и сохранен")
                                else:
                                    logger.error(f"Ошибка сохранения в таблицу для звонка {call_id}")
                            else:
                                logger.warning(f"Не удалось сгенерировать инсайты для звонка {call_id}")
                        else:
                            logger.error("Метод generate_product_insights не найден в LLMProcessor")
                    else:
                        logger.warning(f"Не удалось проанализировать транскрипцию звонка {call_id}")
                else:
                    logger.warning(f"Транскрипция звонка {call_id} слишком короткая или отсутствует: {len(transcript) if transcript else 0} символов")

            self.save_processed_calls()
            logger.info(f"Обработано новых звонков: {new_processed}")
            return new_processed

        except Exception as e:
            logger.error(f"Критическая ошибка в process_new_calls: {e}")
            return 0

    def run_continuously(self, interval_minutes=5):
        logger.info(f"Запуск автоматической обработки с интервалом {interval_minutes} минут")
        self.process_new_calls()  # Первый запуск сразу

        schedule.every(interval_minutes).minutes.do(self.process_new_calls)

        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Остановка сервиса...")
            self.save_processed_calls()
        except Exception as e:
            logger.error(f"Неожиданная ошибка в run_continuously: {e}")
            self.save_processed_calls()

if __name__ == '__main__':
    processor = AutoCallProcessor()
    processor.run_continuously()