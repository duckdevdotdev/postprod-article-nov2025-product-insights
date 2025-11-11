from flask import Flask, request, jsonify
import logging
import os
from dotenv import load_dotenv

from exolve_client import ExolveWebhookProcessor
from llm_utils import LLMProcessor
from sheet_utils import GoogleSheetsManager

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

sheets_manager = GoogleSheetsManager()
llm_processor = LLMProcessor()
webhook_processor = ExolveWebhookProcessor(sheets_manager, llm_processor)

@app.route('/webhook/exolve', methods=['POST'])
def handle_exolve_webhook():
    try:
        logger.info(f"Вебхук: {request.json}")

        auth_token = request.headers.get('Authorization')
        expected_token = os.getenv('WEBHOOK_SECRET_TOKEN')

        if expected_token and auth_token != f"Bearer {expected_token}":
            return jsonify({"status": "error", "message": "Unauthorized"}), 401

        event_data = request.json
        success = webhook_processor.process_webhook_event(event_data)

        if success:
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error"}), 500

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return jsonify({"status": "error"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    host = os.getenv('WEBHOOK_HOST', '0.0.0.0')
    port = int(os.getenv('WEBHOOK_PORT', '5000'))
    app.run(host=host, port=port, debug=False)