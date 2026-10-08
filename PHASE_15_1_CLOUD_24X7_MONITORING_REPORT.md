# Phase 15.1 — Cloud 24/7 Monitoring Deployment

## 1. Deployment Architecture
- **Environment:** Ubuntu Linux VPS.
- **Service Type:** `systemd` daemon (`monitoring-worker.service`).
- **Runtime:** Python 3.11 virtual environment.
- **Goal:** Continuously observe real-world market and portfolio data and notify on meaningful changes without breaking the Phase 11 safety boundaries.

## 2. Security Controls & Environment Isolation
- Uses a dedicated `stockbot` user without root privileges.
- Environment variables (`.env`) govern all credentials and are explicitly ignored from Git (`.env.example` has been updated with safe placeholders only).
- **Hard Boundaries:** `app/worker/monitoring_worker.py` contains 0 imports or references to `OrderIntent`, `execute_confirmed_order`, or any execution pathways.
- The `systemd` unit file uses `NoNewPrivileges=true` and `ProtectSystem=full` for enhanced system hardening.

## 3. Worker Monitoring Flow & State
The `monitoring_worker.py` performs the following cyclically:
1. Validates Angel One Authentication.
2. Performs real `getRMS`, `getHolding`, and `getPosition` calls.
3. Retrieves real Screener fundamental data.
4. Updates health tracking inside `monitoring_health.json`.
5. Logs decisions dynamically into `monitoring_state.json`.
6. Triggers a payload to Telegram (`TelegramNotificationService`) only on actionable or materialized changes (`BUY`, `SELL`, `REDUCE`, or `BUY` to `WATCH` invalidations).
7. Sleeps for `MONITORING_INTERVAL_SECONDS`.

## 4. Test Results
- **Unit Tests:** `test_monitoring_worker.py` was extended to verify authentication fail-safes, notification deduping, and safety boundary constraints (asserting that `OrderIntent` and `confirm_order` are fundamentally disconnected from the worker).
- **Backend Tests:** 312/312 tests passed successfully.
- **Dry Run Validation:** A complete live run against real Angel One data was performed, logging `Cycle completed successfully` without raising any HTTP execution calls. 

## 5. Git Status
No credentials or secret values were tracked. The `.env` overrides are secure. 

## 6. Known Limitations
- Network disconnects from Angel One will safely mark the cycle as `DATA_FAILED` in health checks and sleep until the next cycle to prevent API spam. 

## 7. Status
**24/7 cloud deployment configuration READY — cloud deployment NOT YET EXECUTED.**

The local pipeline has been completely vetted against the production target configuration, and systemd files are ready to be installed on your VPS.
