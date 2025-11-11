import time
import schedule
import logging
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

from exolve_client import ExolveClient
from llm_utils import LLMProcessor
from sheets_utils import GoogleSheetsManager

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
            logger.error(f"Ошибка загрузки: {e}")

    def save_processed_calls(self):
        try:
            with open('processed_calls.txt', 'w') as f:
                for call_id in self.processed_call_ids:
                    f.write(f"{call_id}\n")
        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")

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

                transcript = self.exolve_client.get_call_transcript(call_id)
                if transcript and len(transcript) > 100:
                    analysis = self.llm_processor.analyze_call(transcript)
                    if analysis:
                        creatives = self.llm_processor.generate_creatives(analysis)
                        success = self.sheets_manager.append_analysis(
                            os.getenv("GOOGLE_SHEETS_URL"),
                            analysis,
                            creatives
                        )
                        if success:
                            self.processed_call_ids.add(call_id)
                            new_processed += 1

            self.save_processed_calls()
            logger.info(f"Обработано новых: {new_processed}")
            return new_processed

        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return 0

    def run_continuously(self, interval_minutes=5):
        logger.info(f"Запуск с интервалом {interval_minutes} минут")
        self.process_new_calls()
        schedule.every(interval_minutes).minutes.do(self.process_new_calls)

        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Остановка...")
            self.save_processed_calls()

if __name__ == '__main__':
    processor = AutoCallProcessor()
    processor.run_continuously()