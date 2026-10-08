# FINAL SETUP INSTRUCTIONS

To run the AI Autonomous Long-Term Investment System securely in read-only mode:

1. **Environment Variables**:
   ```env
   # Ensure live trading remains strictly disabled
   ENABLE_LIVE_TRADING=false
   BROKER_EXECUTION_BLOCKED=true
   LIVE_EXECUTION_UNLOCKED=false
   
   # Angel One Authentication
   ANGEL_ONE_CLIENT_ID=your_client_id
   ANGEL_ONE_PASSWORD=your_password
   ANGEL_ONE_API_KEY=your_api_key
   ANGEL_ONE_TOTP_SECRET=your_totp_secret
   ```
2. **Run Pytest**:
   ```bash
   pytest tests/
   ```
   (Verify all 337+ tests pass to ensure shadow execution integrity).
3. **Run Autonomous Cycle (Read-Only)**:
   ```bash
   python cli_autonomous_cycle.py
   ```
   This will pull live market data, evaluate holdings against `ScreenerFundamentalDataProvider`, generate `OrderIntents`, and block them from executing.
