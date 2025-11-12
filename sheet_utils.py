import os
import json
import gspread
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = [
    "Timestamp",
    "Main Problem",
    "Key Fear",
    "Desired Solution",
    "Original Phrases",
    "Tags",
]


class GoogleSheetsManager:
    """
    Минимальный менеджер для работы с Google Sheets.
    Аутентификация:
      1) через путь к файлу сервисного аккаунта (ENV GOOGLE_SERVICE_ACCOUNT_FILE), или
      2) через JSON сервисного аккаунта в ENV GOOGLE_SERVICE_ACCOUNT_JSON.
    Можно также передать credentials_file / credentials_json прямо в конструктор.
    """

    def __init__(
            self,
            credentials_file: Optional[str] = None,
            credentials_json: Optional[str] = None,
    ):
        self.client: Optional[gspread.Client] = None
        self._authenticate(credentials_file, credentials_json)

    def _authenticate(
            self,
            credentials_file: Optional[str],
            credentials_json: Optional[str],
    ):
        try:
            # 1) приоритет — явные аргументы
            if credentials_file:
                self.client = gspread.service_account(filename=credentials_file)
            elif credentials_json:
                info = json.loads(credentials_json)
                self.client = gspread.service_account_from_dict(info)
            else:
                # 2) ENV переменные
                env_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
                env_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
                if env_file:
                    self.client = gspread.service_account(filename=env_file)
                elif env_json:
                    info = json.loads(env_json)
                    self.client = gspread.service_account_from_dict(info)
                else:
                    # 3) дефолт — локальный файл service_account.json (если есть)
                    default_file = "service_account.json"
                    if os.path.exists(default_file):
                        self.client = gspread.service_account(filename=default_file)
                    else:
                        raise RuntimeError(
                            "Не найден сервисный аккаунт. "
                            "Укажи GOOGLE_SERVICE_ACCOUNT_FILE или GOOGLE_SERVICE_ACCOUNT_JSON."
                        )

            logger.info("Аутентификация в Google Sheets успешна")
        except Exception as e:
            logger.error(f"Ошибка аутентификации Google Sheets: {e}")
            raise

    def _open_sheet(self, sheet_url: str):
        return self.client.open_by_url(sheet_url).sheet1

    def ensure_headers(self, sheet_url: str, headers: Optional[List[str]] = None) -> bool:
        """Создаёт заголовки в первой строке, если их нет."""
        try:
            ws = self._open_sheet(sheet_url)
            headers = headers or DEFAULT_HEADERS
            existing = ws.row_values(1)
            if not existing:
                ws.append_row(headers)
                logger.info("Созданы заголовки таблицы")
            return True
        except Exception as e:
            logger.error(f"Ошибка ensure_headers: {e}")
            return False

    def append_analysis(
            self,
            sheet_url: str,
            analysis_data: Dict[str, Any],
            insights_data: Dict[str, Any],
    ) -> bool:
        try:
            ws = self._open_sheet(sheet_url)

            row_data = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                analysis_data.get("main_problem", ""),
                analysis_data.get("key_fear", ""),
                analysis_data.get("result_solution", ""),
                " | ".join(analysis_data.get("original_phrases", []) or []),
                " | ".join(analysis_data.get("tags", []) or []),
                "авто-анализ",
            ]

            ws.append_row(row_data)
            logger.info("Данные добавлены в таблицу")
            return True
        except Exception as e:
            logger.error(f"Ошибка добавления данных в таблицу: {e}")
            return False

    def get_sheet_data(self, sheet_url: str) -> Optional[List[Dict]]:
        try:
            ws = self._open_sheet(sheet_url)
            return ws.get_all_records()
        except Exception as e:
            logger.error(f"Ошибка получения данных из таблицы: {e}")
            return None

    def create_sheet_if_not_exists(self, sheet_url: str) -> bool:
        """Создаёт заголовки, если их ещё нет (таблица уже должна существовать)."""
        return self.ensure_headers(sheet_url)


# ——— Опциональный «глобальный» синглтон ———
_sheets_manager: Optional[GoogleSheetsManager] = None


def get_sheets_manager() -> GoogleSheetsManager:
    global _sheets_manager
    if _sheets_manager is None:
        _sheets_manager = GoogleSheetsManager()
    return _sheets_manager


def append_to_google_sheet(
        analysis_data: Dict[str, Any],
        insights_data: Dict[str, Any],
        sheet_url: str,
) -> bool:
    try:
        return get_sheets_manager().append_analysis(sheet_url, analysis_data, insights_data)
    except Exception as e:
        logger.error(f"Ошибка append_to_google_sheet: {e}")
        return False


def get_google_sheet_data(sheet_url: str) -> Optional[List[Dict]]:
    try:
        return get_sheets_manager().get_sheet_data(sheet_url)
    except Exception as e:
        logger.error(f"Ошибка get_google_sheet_data: {e}")
        return None


def init_google_sheet(sheet_url: str) -> bool:
    try:
        return get_sheets_manager().create_sheet_if_not_exists(sheet_url)
    except Exception as e:
        logger.error(f"Ошибка init_google_sheet: {e}")
        return False
