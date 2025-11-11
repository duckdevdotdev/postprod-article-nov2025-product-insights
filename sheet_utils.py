import gspread
from datetime import datetime
from typing import Dict, Any, List, Optional
from config import SHEETS_CONFIG
import logging

logger = logging.getLogger(__name__)


class GoogleSheetsManager:
    def __init__(self):
        self.client = None
        self._authenticate()

    def _authenticate(self):
        try:
            self.client = gspread.service_account(filename=SHEETS_CONFIG["credentials_file"])
            logger.info("Аутентификация успешна")
        except Exception as e:
            logger.error(f"Ошибка аутентификации: {e}")
            raise

    # В sheet_utils.py в методе append_analysis обновить поля:
    def append_analysis(self, sheet_url: str, analysis_data: Dict[str, Any], creatives_data: Dict[str, Any]) -> bool:
        try:
            spreadsheet = self.client.open_by_url(sheet_url)
            worksheet = spreadsheet.sheet1

            row_data = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                analysis_data.get("main_problem", ""),
                analysis_data.get("key_fear", ""),  # Изменено с key_objection
                analysis_data.get("result_solution", ""),
                " | ".join(analysis_data.get("original_phrases", [])),
                " | ".join(analysis_data.get("tags", [])),
                " | ".join(creatives_data.get("headlines", [])),
                " | ".join(creatives_data.get("ad_texts", [])),
                "авто-анализ"
            ]

            worksheet.append_row(row_data)
            logger.info("Данные добавлены в таблицу")
            return True

        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return False

    def get_sheet_data(self, sheet_url: str) -> Optional[List[Dict]]:
        try:
            spreadsheet = self.client.open_by_url(sheet_url)
            worksheet = spreadsheet.sheet1
            return worksheet.get_all_records()
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            return None

    _sheets_manager = None


def get_sheets_manager():
    global _sheets_manager
    if _sheets_manager is None:
        _sheets_manager = GoogleSheetsManager()
    return _sheets_manager


def append_to_google_sheet(analysis_data: Dict[str, Any], creatives_data: Dict[str, Any], sheet_url: str) -> bool:
    try:
        manager = get_sheets_manager()
        return manager.append_analysis(sheet_url, analysis_data, creatives_data)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return False


def get_google_sheet_data(sheet_url: str) -> Optional[List[Dict]]:
    try:
        manager = get_sheets_manager()
        return manager.get_sheet_data(sheet_url)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return None
