import os
import sys
import time
import pyotp
from datetime import datetime, timezone

def diagnose():
    print("=== ANGEL ONE AUTHENTICATION DIAGNOSTIC ===")
    
    # 1. Which .env is loaded
    env_path = os.path.join(os.getcwd(), '.env')
    print(f"1. Checking {env_path}")
    if os.path.exists(env_path):
        print("   Found .env file in current directory.")
    else:
        print("   WARNING: .env not found in current directory.")
        
    try:
        from app.core.config import settings
        print("   settings loaded from app.core.config successfully.")
    except Exception as e:
        print(f"   Failed to load settings: {e}")
        return

    # 2. ANGEL_ONE_CLIENT_ID (masked)
    client_id = settings.ANGEL_ONE_CLIENT_ID
    if client_id:
        masked_id = client_id[:4] + "*" * (len(client_id) - 4) if len(client_id) > 4 else "****"
        print(f"\n2. CLIENT_ID: Loaded. Masked value: {masked_id}")
    else:
        print("\n2. CLIENT_ID: MISSING or EMPTY.")

    # 3. & 4. ANGEL_ONE_TOTP_SECRET length & whitespace check
    totp_secret = settings.ANGEL_ONE_TOTP_SECRET
    if totp_secret:
        print(f"\n3. TOTP_SECRET: Exists. Length: {len(totp_secret)} chars.")
        
        has_whitespace = False
        if totp_secret != totp_secret.strip():
            has_whitespace = True
            print("4. WARNING: TOTP_SECRET contains leading or trailing whitespace!")
        else:
            print("4. TOTP_SECRET formatting: Clean (No leading/trailing whitespace detected).")
            
        if totp_secret.startswith('"') or totp_secret.endswith('"') or totp_secret.startswith("'") or totp_secret.endswith("'"):
            print("   WARNING: TOTP_SECRET is wrapped in quotes!")
        
        if len(totp_secret) < 16:
            print("   WARNING: TOTP_SECRET length is unusually short for a Base32 string.")
    else:
        print("\n3. TOTP_SECRET: MISSING or EMPTY.")
        print("4. TOTP_SECRET formatting check: SKIPPED (Missing).")

    # 5. TOTP Generator Test
    if totp_secret:
        try:
            totp = pyotp.TOTP(totp_secret.strip())
            current_code = totp.now()
            print("\n5. TOTP Generator: Successfully generated a 6-digit code using the loaded secret.")
        except Exception as e:
            print(f"\n5. TOTP Generator: FAILED. Error: {e}")
    else:
        print("\n5. TOTP Generator check: SKIPPED (Missing secret).")

    # 6. System Clock / Timezone
    print("\n6. System Clock & Timezone:")
    local_now = datetime.now()
    utc_now = datetime.now(timezone.utc)
    print(f"   Local Time: {local_now}")
    print(f"   UTC Time:   {utc_now}")
    
    # Check for pyotp time skew if we want (it uses time.time())
    print(f"   time.time(): {time.time()}")

if __name__ == "__main__":
    diagnose()
