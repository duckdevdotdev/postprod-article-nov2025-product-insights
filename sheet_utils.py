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

    def append_analysis(self, sheet_url: str, analysis_data: Dict[str, Any], insights_data: Dict[str, Any]) -> bool:
        try:
            spreadsheet = self.client.open_by_url(sheet_url)
            worksheet = spreadsheet.sheet1

            # Подготовка данных для строки
            row_data = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                analysis_data.get("main_problem", ""),
                analysis_data.get("key_fear", ""),
                analysis_data.get("result_solution", ""),
                " | ".join(analysis_data.get("original_phrases", [])),
                " | ".join(analysis_data.get("tags", [])),
                # Продуктовые инсайты
                " | ".join(insights_data.get("product_insights", [])),
                " | ".join(insights_data.get("feature_suggestions", [])),
                " | ".join(insights_data.get("ux_improvements", [])),
                insights_data.get("priority_level", "medium"),
                "авто-анализ"
            ]

            worksheet.append_row(row_data)
            logger.info("Данные добавлены в таблицу")
            return True

        except Exception as e:
            logger.error(f"Ошибка добавления данных в таблицу: {e}")
            return False

    def get_sheet_data(self, sheet_url: str) -> Optional[List[Dict]]:
        try:
            spreadsheet = self.client.open_by_url(sheet_url)
            worksheet = spreadsheet.sheet1
            return worksheet.get_all_records()
        except Exception as e:
            logger.error(f"Ошибка получения данных из таблицы: {e}")
            return None

    def create_sheet_if_not_exists(self, sheet_url: str) -> bool:
        """Создает таблицу с заголовками если она не существует"""
        try:
            spreadsheet = self.client.open_by_url(sheet_url)
            worksheet = spreadsheet.sheet1

            # Проверяем есть ли заголовки
            existing_headers = worksheet.row_values(1)
            if not existing_headers:
                headers = [
                    "Timestamp",
                    "Main Problem",
                    "Key Fear",
                    "Desired Solution",
                    "Original Phrases",
                    "Tags",
                    "Product Insights",
                    "Feature Suggestions",
                    "UX Improvements",
                    "Priority Level",
                    "Source"
                ]
                worksheet.append_row(headers)
                logger.info("Созданы заголовки таблицы")

            return True
        except Exception as e:
            logger.error(f"Ошибка создания таблицы: {e}")
            return False


# Глобальный менеджер для singleton pattern
_sheets_manager = None


def get_sheets_manager():
    global _sheets_manager
    if _sheets_manager is None:
        _sheets_manager = GoogleSheetsManager()
    return _sheets_manager


def append_to_google_sheet(analysis_data: Dict[str, Any], insights_data: Dict[str, Any], sheet_url: str) -> bool:
    try:
        manager = get_sheets_manager()
        return manager.append_analysis(sheet_url, analysis_data, insights_data)
    except Exception as e:
        logger.error(f"Ошибка добавления в Google Sheet: {e}")
        return False


def get_google_sheet_data(sheet_url: str) -> Optional[List[Dict]]:
    try:
        manager = get_sheets_manager()
        return manager.get_sheet_data(sheet_url)
    except Exception as e:
        logger.error(f"Ошибка получения данных из Google Sheet: {e}")
        return None


def init_google_sheet(sheet_url: str) -> bool:
    """Инициализирует таблицу с заголовками"""
    try:
        manager = get_sheets_manager()
        return manager.create_sheet_if_not_exists(sheet_url)
    except Exception as e:
        logger.error(f"Ошибка инициализации Google Sheet: {e}")
        return False
