# FINAL ARCHITECTURE

The AI Autonomous Long-Term Investment & Portfolio Management System is built on a robust, modular backend designed strictly for read-only tracking and analysis.

## Core Modules
1. **Market Data Service**: Handles all raw extraction of data via provider implementations (Angel One, Mock).
2. **Fundamental Provider Registry**: Abstract layer managing multiple sources of fundamental data (Screener.in).
3. **Decision Engine**: Processes risk, fundamentals, technical momentum, and valuation to emit investment actions.
4. **Portfolio Manager**: Evaluates live cash, live holdings, open positions, and aggregates decisions.
5. **Execution Readiness Layer**: Validates safety rules before producing `OrderIntents`.
6. **Live Broker Execution Guard**: A hardcoded safety net ensuring that no actual live order is ever placed while in Read-Only Mode.

The entire flow is strictly supervised and logged via `decisions_audit.jsonl` and `order_intent_audit.jsonl`.
