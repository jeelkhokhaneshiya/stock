import logging
import httpx
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class NotificationService:
    def send_notification(self, message: str) -> bool:
        raise NotImplementedError()

class TelegramNotificationService(NotificationService):
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or getattr(settings, "TELEGRAM_BOT_TOKEN", None)
        self.chat_id = chat_id or getattr(settings, "TELEGRAM_CHAT_ID", None)
        
    def send_notification(self, message: str) -> bool:
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram credentials not configured, skipping notification.")
            return False
            
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        try:
            # Synchronous HTTP call for simplicity, but could be async
            response = httpx.post(url, json=payload, timeout=10.0)
            response.raise_for_status()
            logger.info("Sent Telegram notification.")
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            return False

class MockNotificationService(NotificationService):
    def __init__(self):
        self.messages = []
        
    def send_notification(self, message: str) -> bool:
        self.messages.append(message)
        logger.info(f"Mock notification sent: {message}")
        return True

def get_notification_service() -> NotificationService:
    if getattr(settings, "TESTING", False) or not getattr(settings, "TELEGRAM_BOT_TOKEN", None):
        return MockNotificationService()
    return TelegramNotificationService()
