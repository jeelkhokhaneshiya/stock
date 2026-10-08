# Phase 15 — 24/7 Real Investment Monitoring & Phone Notifications

## Objective
Implement a continuous monitoring service running 24/7 on a server that notifies the user on their phone of actionable real-money investment decisions (BUY, BUY_MORE, REDUCE, SELL) without bypassing the mandatory Phase 11 human confirmation execution boundary.

## Implementation Details

1. **Continuous Monitoring Service:**
   - **File:** `app/worker/monitoring_worker.py`
   - **Flow:** Authenticates via `AngelOneAuth` -> Fetches real portfolio snapshot -> Runs decision engine -> Tracks state -> Sends notification.
   - **State Persistence:** Preserves last-known recommendations in a local JSON state file (`monitoring_state.json`) to prevent duplicate spam notifications.
   - **Interval:** Runs cyclically based on `MONITORING_INTERVAL_SECONDS` (default: 3600 seconds / 1 hour).
   
2. **Notification Provider:**
   - **Provider:** Telegram API (implemented via `TelegramNotificationService`).
   - **Usage:** Configured via `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` environment variables. If not configured, gracefully falls back to mock console notifications.
   
3. **Execution Safety Boundary:**
   - The monitoring service `monitoring_worker.py` **never** imports or triggers `OrderIntent`, `create_order_preview`, or `execute_confirmed_order`. 
   - Notifications act solely as read-only alerts.
   - The user must still explicitly confirm any order in the normal application UI/flow.

## Notification Rules Implemented
- **New Decisions:** Notifies on any new `BUY`, `BUY_MORE`, `SELL`, or `REDUCE`.
- **Material Changes:** Notifies if an existing decision changes in quantity (qty > 5 diff).
- **Invalidations:** Notifies if a previous `BUY`/`BUY_MORE` opportunity becomes invalid (`WATCH`, `HOLD`, `NO_ACTION`) due to stale data or broken fundamental thesis.
- **Deduplication:** Repeated unchanged decisions do not trigger new notifications.

## Tests Added and Passed
All 7 added tests passed locally in `tests/test_monitoring_worker.py`:
- `test_buy_notification`: Verifies BUY notification triggers and saves state.
- `test_unchanged_decision_no_notification`: Ensures no spam for unchanged decisions.
- `test_sell_notification`: Verifies SELL triggers notification.
- `test_invalidation_notification`: Verifies that a BUY turning to WATCH triggers a notification.
- `test_authentication_failure`: Verifies the worker alerts on auth failure and doesn't crash.
- `test_notification_failure_does_not_save_state`: Ensures failed network requests don't skip state tracking.
- `test_worker_cannot_bypass_confirmation`: Verifies the worker is physically disconnected from execution interfaces.

## Local Running Instructions
To run the monitoring service locally:
```bash
# Ensure TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set in .env (optional)
set MONITORING_INTERVAL_SECONDS=3600
python -m app.worker.monitoring_worker
```
*(Use `export` instead of `set` if using bash/zsh).*

**Note:** No automatic order execution was added. Real orders still require explicit human confirmation.
