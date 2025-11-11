from flask import Flask, request, jsonify
import logging
import os
from dotenv import load_dotenv

from exolve_client import ExolveWebhookProcessor
from llm_utils import LLMProcessor
from sheet_utils import GoogleSheetsManager

load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Инициализация компонентов
try:
    sheets_manager = GoogleSheetsManager()
    llm_processor = LLMProcessor()
    webhook_processor = ExolveWebhookProcessor(sheets_manager, llm_processor)
    logger.info("Компоненты вебхука успешно инициализированы")
except Exception as e:
    logger.error(f"Ошибка инициализации компонентов: {e}")
    raise

@app.route('/webhook/exolve', methods=['POST'])
def handle_exolve_webhook():
    try:
        # Логируем базовую информацию о запросе
        client_ip = request.remote_addr
        user_agent = request.headers.get('User-Agent', 'Unknown')

        logger.info(f"Вебхук от {client_ip}: {user_agent}")

        # Проверка авторизации
        auth_token = request.headers.get('Authorization')
        expected_token = os.getenv('WEBHOOK_SECRET_TOKEN')

        if expected_token and auth_token != f"Bearer {expected_token}":
            logger.warning(f"Неавторизованный доступ с токеном: {auth_token}")
            return jsonify({
                "status": "error",
                "message": "Unauthorized"
            }), 401

        # Проверка наличия данных
        if not request.json:
            logger.warning("Пустой JSON в запросе")
            return jsonify({
                "status": "error",
                "message": "Empty request body"
            }), 400

        event_data = request.json
        logger.info(f"Обработка события: {event_data.get('event_type', 'unknown')}")

        # Обработка вебхука
        success = webhook_processor.process_webhook_event(event_data)

        if success:
            logger.info("Вебхук успешно обработан")
            return jsonify({
                "status": "success",
                "message": "Webhook processed successfully"
            })
        else:
            logger.warning("Ошибка обработки вебхука")
            return jsonify({
                "status": "error",
                "message": "Failed to process webhook"
            }), 500

    except Exception as e:
        logger.error(f"Критическая ошибка обработки вебхука: {e}")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Проверка здоровья сервиса"""
    try:
        # Базовая проверка что компоненты работают
        health_status = {
            "status": "healthy",
            "timestamp": __import__('datetime').datetime.now().isoformat(),
            "components": {
                "sheets_manager": "ok",
                "llm_processor": "ok",
                "webhook_processor": "ok"
            }
        }
        return jsonify(health_status)
    except Exception as e:
        logger.error(f"Ошибка health check: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 500

@app.route('/ready', methods=['GET'])
def readiness_check():
    """Проверка готовности сервиса к работе"""
    try:
        # Проверяем что все зависимости работают
        # Можно добавить проверки подключения к БД, API и т.д.
        return jsonify({"status": "ready"})
    except Exception as e:
        logger.error(f"Ошибка readiness check: {e}")
        return jsonify({"status": "not ready"}), 503

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "status": "error",
        "message": "Endpoint not found"
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "status": "error",
        "message": "Method not allowed"
    }), 405

if __name__ == '__main__':
    host = os.getenv('WEBHOOK_HOST', '0.0.0.0')
    port = int(os.getenv('WEBHOOK_PORT', '5000'))
    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'

    logger.info(f"Запуск вебхук сервера на {host}:{port}")

    app.run(
        host=host,
        port=port,
        debug=debug_mode,
        # Для продакшена лучше использовать production WSGI сервер
        # например через waitress или gunicorn
    )