# REAL EXECUTION SETUP

The system defaults to `SHADOW` execution mode. To perform real trades, you MUST explicitly enable the `CONFIRMATION_REQUIRED` mode.

1. Ensure real API credentials are provided in `.env`:
   ```bash
   ANGEL_ONE_API_KEY=YOUR_API_KEY
   ANGEL_ONE_CLIENT_ID=YOUR_CLIENT_ID
   ANGEL_ONE_PASSWORD=YOUR_PASSWORD
   ANGEL_ONE_TOTP_SECRET=YOUR_TOTP
   ```

2. Inside `app/core/config.py`, change:
   ```python
   EXECUTION_MODE = "CONFIRMATION_REQUIRED"
   ```

3. Ensure the Kill Switch is OFF:
   ```python
   AUTONOMOUS_KILL_SWITCH = False
   ```

4. The autonomous cycle will now begin producing `OrderPreview` intents. They will NOT execute. You must programmatically or manually extract these previews via the execution engine and explicitly submit an `OrderConfirmation` to trigger the actual broker submission.
