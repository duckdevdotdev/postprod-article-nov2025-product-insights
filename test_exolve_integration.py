import os
import sys
import json
from dotenv import load_dotenv
from exolve_client import ExolveClient

load_dotenv()


def test_exolve_integration():
    print("Тестирование Exolve API...")

    api_key = os.getenv("EXOLVE_API_KEY")
    if not api_key:
        print("❌ EXOLVE_API_KEY не найден")
        return False

    client = ExolveClient()

    print("1. Тест подключения...")
    calls = client.get_recent_calls(hours_back=24)  # Увеличим период для теста
    print(f"Найдено звонков: {len(calls)}")

    if calls:
        call_id = calls[0].get("id")
        if call_id:
            print(f"2. Тест деталей звонка для {call_id}...")
            call_details = client.get_call_details(call_id)
            if call_details:
                print("Доступные ключи в данных звонка:")
                print(json.dumps(list(call_details.keys()), indent=2))

                # Сохраним полный ответ для анализа
                with open("call_details_debug.json", "w", encoding="utf-8") as f:
                    json.dump(call_details, f, ensure_ascii=False, indent=2)
                print("Полные данные сохранены в call_details_debug.json")

            print(f"3. Тест расшифровки для {call_id}...")
            transcript = client.get_call_transcript(call_id)
            if transcript:
                print(f"✅ Расшифровка получена: {len(transcript)} символов")
                print(f"Предпросмотр: {transcript[:200]}...")
            else:
                print("❌ Расшифровка не получена")
    else:
        print("❌ Не найдено звонков для теста")

    return True


if __name__ == "__main__":
    test_exolve_integration()
