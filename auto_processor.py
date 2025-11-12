import logging
import os
import time
from datetime import datetime
import schedule
from dotenv import load_dotenv

from exolve_client import ExolveClient
from llm_utils import LLMProcessor
from sheet_utils import GoogleSheetsManager

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

PROCESSED_FILE = "processed_calls.txt"


class AutoCallProcessor:
    def __init__(self, min_transcript_len: int = 100):
        self.exolve_client = ExolveClient()
        self.llm = LLMProcessor()
        self.sheets = GoogleSheetsManager()
        self.sheet_url = os.getenv("GOOGLE_SHEETS_URL")
        if not self.sheet_url:
            raise RuntimeError("GOOGLE_SHEETS_URL is not set")

        self.min_transcript_len = min_transcript_len
        self.processed_uids = self._load_processed()

    def _load_processed(self):
        if not os.path.exists(PROCESSED_FILE):
            return set()
        with open(PROCESSED_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())

    def _save_processed(self):
        with open(PROCESSED_FILE, "w") as f:
            for uid in sorted(self.processed_uids):
                f.write(f"{uid}\n")

    def process_new_calls(self) -> int:
        logger.info("Проверка новых звонков...")
        calls = self.exolve_client.get_recent_calls(hours_back=1)
        logger.info(f"Найдено звонков: {len(calls)}")

        processed_now = 0
        for call in calls:
            uid = call.get("uid") or call.get("id")
            if not uid or str(uid) in self.processed_uids:
                continue

            logger.info(f"Обработка звонка uid={uid}")
            transcript = self.exolve_client.get_call_transcript(int(uid))
            if not transcript or len(transcript) < self.min_transcript_len:
                logger.info(f"Транскрипт отсутствует или короткий (len={len(transcript) if transcript else 0})")
                continue

            analysis = self.llm.analyze_call(transcript)
            if not analysis:
                logger.warning(f"LLM-анализ не вернул результат (uid={uid})")
                continue

            insights = self.llm.generate_product_insights(analysis)
            if not insights:
                logger.warning(f"Инсайты не сгенерированы (uid={uid})")
                continue

            ok = self.sheets.append_analysis(self.sheet_url, analysis, insights)
            if ok:
                self.processed_uids.add(str(uid))
                processed_now += 1
                logger.info(f"Звонок {uid} сохранён в Google Sheets")
            else:
                logger.error(f"Ошибка сохранения звонка {uid} в Google Sheets")

        if processed_now:
            self._save_processed()
        logger.info(f"Обработано новых звонков: {processed_now}")
        return processed_now

    def run_continuously(self, interval_minutes=5):
        logger.info(f"Запуск с интервалом {interval_minutes} мин.")
        self.process_new_calls()
        schedule.every(interval_minutes).minutes.do(self.process_new_calls)
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Остановка сервиса...")
            self._save_processed()


if __name__ == "__main__":
    AutoCallProcessor().run_continuously()
