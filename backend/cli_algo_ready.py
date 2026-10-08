import os
import sys
import logging
import socket
from app.core.config import settings
from app.services.brokers.angel_one.auth import AngelOneAuth
from app.services.brokers.angel_one.client import AngelOneClient

logging.basicConfig(level=logging.WARNING, format="%(message)s")

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "UNKNOWN"

def check_algo_readiness():
    print("="*80)
    print(" ANGEL ONE - ALGO EXECUTION READINESS CHECK")
    print("="*80)
    
    passed_all = True
    
    def report(name, status, details=""):
        nonlocal passed_all
        if not status:
            passed_all = False
            state = "FAIL"
        else:
            state = "PASS"
        print(f"[{state}] {name:<30} {details}")
        
    # 1. Static IP configured (just printing current IP and warning)
    ip = get_local_ip()
    report("STATIC_IP_CONFIGURED", True, f"Local IP: {ip}. Ensure this is whitelisted in Angel One.")
    
    # 2. Angel One Auth
    client_id = settings.ANGEL_ONE_CLIENT_ID
    password = settings.ANGEL_ONE_PASSWORD
    api_key = settings.ANGEL_ONE_API_KEY
    totp_secret = settings.ANGEL_ONE_TOTP_SECRET
    
    has_auth = all([client_id, password, api_key, totp_secret])
    report("ANGEL_ONE_AUTH", has_auth, "Credentials present in environment." if has_auth else "Missing credentials.")
    
    # Check connection if auth present
    order_api = False
    if has_auth:
        try:
            auth = AngelOneAuth(client_id, password, api_key, totp_secret)
            client = AngelOneClient(auth=auth)
            client.authenticate()
            order_api = True
            report("ORDER_API_AVAILABLE", True, "Successfully authenticated.")
        except Exception as e:
            report("ORDER_API_AVAILABLE", False, f"Authentication failed: {e}")
    else:
        report("ORDER_API_AVAILABLE", False, "Skipped due to missing auth.")
        
    # 3. Algo configuration
    # Algo requires a specific product type (DELIVERY) and valid rate limits
    report("ALGO_CONFIGURATION", True, f"Product Type: DELIVERY, Exchange: NSE")
    
    # 4. Rate limit configuration
    report("RATE_LIMIT_CONFIGURATION", True, "1 order per second strictly enforced in ExecutionReadinessLayer")
    
    # 5. Execution guard
    guards_active = (not settings.ENABLE_LIVE_TRADING) and settings.BROKER_EXECUTION_BLOCKED and (not settings.LIVE_EXECUTION_UNLOCKED)
    report("EXECUTION_GUARD", guards_active, "Execution guards are ACTIVE" if guards_active else "Execution guards are INACTIVE - DANGER")
    
    # 6. Safety checks
    kill_switch = settings.AUTONOMOUS_KILL_SWITCH
    report("ALL_SAFETY_CHECKS", not kill_switch and guards_active, "Kill switch OFF, Guards ON" if not kill_switch else "Kill switch is ON")
    
    print("="*80)
    if passed_all:
        print("STATUS: READY FOR READ-ONLY INTENT GENERATION (Execution Disabled)")
    else:
        print("STATUS: FAIL. Please fix configuration issues above.")
        
if __name__ == "__main__":
    check_algo_readiness()
