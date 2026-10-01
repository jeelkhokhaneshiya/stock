import pyotp
import logging
from typing import Optional, Dict
from app.core.config import settings
from app.services.brokers.angel_one.exceptions import AngelOneAuthenticationError

logger = logging.getLogger(__name__)

class AngelOneAuth:
    def __init__(self, api_key: str, client_id: str, password: str, totp_secret: str):
        self.api_key = api_key
        self.client_id = client_id
        self.password = password
        self.totp_secret = totp_secret
        
        self.jwt_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.feed_token: Optional[str] = None

    def generate_totp(self) -> str:
        """Isolate TOTP generation so secret is not leaked."""
        if not self.totp_secret:
            raise AngelOneAuthenticationError("TOTP secret is missing")
        try:
            totp = pyotp.TOTP(self.totp_secret)
            return totp.now()
        except Exception as e:
            logger.error("Failed to generate TOTP")
            raise AngelOneAuthenticationError(f"TOTP generation failed: {str(e)}")

    def set_tokens(self, jwt_token: str, refresh_token: str, feed_token: str):
        self.jwt_token = jwt_token
        self.refresh_token = refresh_token
        self.feed_token = feed_token
        
    def clear_tokens(self):
        self.jwt_token = None
        self.refresh_token = None
        self.feed_token = None
        
    def get_auth_headers(self) -> Dict[str, str]:
        if not self.jwt_token:
            raise AngelOneAuthenticationError("Not authenticated")
            
        return {
            "Authorization": f"Bearer {self.jwt_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": "127.0.0.1",
            "X-ClientPublicIP": "127.0.0.1",
            "X-MACAddress": "00:00:00:00:00:00",
            "X-PrivateKey": self.api_key
        }

    def is_authenticated(self) -> bool:
        return bool(self.jwt_token)
