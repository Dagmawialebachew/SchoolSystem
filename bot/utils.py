import requests
import logging

logger = logging.getLogger(__name__)

def send_telegram_message(school, chat_id: str, message: str):
    """Send message via Telegram Bot using Markdown for clickable Pay links."""
    token = school.telegram_bot_token
    if not token:
        logger.warning(f"School '{school.name}' missing bot token, message not sent to {chat_id}")
        return

    TELEGRAM_API_URL = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        response = requests.post(
            TELEGRAM_API_URL,
            json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
            timeout=5,
        )
        if response.status_code != 200:
            logger.error(
                f"Failed to send Telegram message to {chat_id} (School: {school.name}). "
                f"Status: {response.status_code}, Response: {response.text}"
            )
        else:
            logger.info(f"Message sent to {chat_id} (School: {school.name})")
    except requests.exceptions.RequestException:
        logger.exception("Network error while sending Telegram message")
