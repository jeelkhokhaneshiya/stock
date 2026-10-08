from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "AI Investment System"
    APP_ENV: str = "development"
    DEBUG: bool = True
    FRONTEND_ORIGIN: str = "http://localhost:5173"
    
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/investment_db"
    
    # Trading Safety
    TRADING_MODE: str = "paper"
    ENABLE_LIVE_TRADING: bool = False
    AUTONOMOUS_MODE: bool = False
    
    # Phase 11 Execution Safety
    EXECUTION_MODE: str = "SHADOW" # SHADOW, CONFIRMATION_REQUIRED
    LIVE_EXECUTION_UNLOCKED: bool = False
    AUTONOMOUS_KILL_SWITCH: bool = False
    BROKER_EXECUTION_BLOCKED: bool = True
    
    # Configurable Limits
    MAX_PORTFOLIO_ALLOCATION_PERCENT: float = 100.0
    MAX_SINGLE_ASSET_PERCENT: float = 20.0
    MAX_DAILY_SIMULATED_LOSS_PERCENT: float = 5.0
    MAX_SINGLE_ORDER_AMOUNT: float = 100000.0
    DECISION_MAX_AGE_SECONDS: int = 3600
    RISK_APPROVAL_MAX_AGE_SECONDS: int = 1800
    CONFIRMATION_MAX_AGE_SECONDS: int = 300
    MAX_DAILY_INVESTMENT_AMOUNT: float = 500000.0
    MIN_CASH_RESERVE: float = 1000.0
    
    # Market Data
    MARKET_DATA_PROVIDER: str = "mock"
    QUOTE_MAX_AGE_SECONDS: int = 300
    HISTORICAL_DATA_MAX_AGE: int = 86400
    
    # Placeholders for future integrations
    BROKER_PROVIDER: str = "paper"
    ANGEL_ONE_API_KEY: str | None = None
    ANGEL_ONE_CLIENT_ID: str | None = None
    ANGEL_ONE_PASSWORD: str | None = None
    ANGEL_ONE_TOTP_SECRET: str | None = None
    BROKER_API_KEY: str | None = None
    BROKER_API_SECRET: str | None = None
    BROKER_ACCESS_TOKEN: str | None = None
    AI_API_KEY: str | None = None
    MARKET_DATA_API_KEY: str | None = None
    # EODHD Fundamental Provider (isolated — NOT shared with Angel One)
    # Set EODHD_API_TOKEN in .env to activate real fundamental data.
    # Example: EODHD_API_TOKEN=YOUR_REAL_EODHD_TOKEN
    EODHD_API_TOKEN: str | None = None
    INDIAN_API_KEY: str | None = None
    FMP_API_KEY: str | None = None
    FINNHUB_API_KEY: str | None = None
    TWELVE_DATA_API_KEY: str | None = None
    
    # Authentication
    SECRET_KEY: str = "supersecretkey"  # Should be overridden in .env
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
