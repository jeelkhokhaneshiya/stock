# AI Autonomous Long-Term Investment & Portfolio Management System

## Purpose
Phase 1 of the AI Autonomous Investment System provides a foundational Python backend architecture. It establishes the base database schema, authentication, API structure, configuration system, and testing setup. 

**IMPORTANT NOTE**: Phase 1 does not connect to any broker and does not execute real trades. It is purely a scaffolding and foundational phase.

## Architecture
- **Language**: Python 3.12+
- **Framework**: FastAPI
- **Database**: PostgreSQL (SQLAlchemy 2.x, Alembic)
- **Authentication**: JWT, bcrypt
- **Configuration**: Pydantic Settings

## Project Setup

### 1. Virtual Environment
```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# Mac/Linux
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configuration
Copy `.env.example` to `.env` and fill in the values:
```bash
cp .env.example .env
```
Ensure that `DATABASE_URL` is set to your PostgreSQL instance.

### 4. Database Setup
Create a PostgreSQL database named `investment_db`.
Run migrations to create tables:
```bash
# Make sure your PYTHONPATH includes the backend folder if you get import errors
set PYTHONPATH=. 
alembic upgrade head
```

### 5. Running the Application
```bash
uvicorn app.main:app --reload
```
API Documentation will be available at `http://127.0.0.1:8000/docs`.

### 6. Running Tests
```bash
set PYTHONPATH=.
pytest
```

## Market Data Architecture (Phase 3)
The Market Data Layer provides robust, provider-independent access to market quotes, historical data, company information, fundamentals, ETFs, and mutual funds.

- **Supported Data Types**: Current quotes, Historical OHLCV, Company Info, Fundamentals, ETF Info, Mutual Fund Info.
- **Provider Configuration**: Driven by the `MARKET_DATA_PROVIDER` environment variable. The default is `mock`, a deterministic in-memory provider designed for robust testing.
- **Data Freshness**: Responses include a `timestamp` and a boolean `is_stale` flag derived from `QUOTE_MAX_AGE_SECONDS` and `HISTORICAL_DATA_MAX_AGE`.
- **Caching**: Currently uses a lightweight in-memory cache to reduce external provider requests.
- **API Examples**:
  - `GET /api/v1/market/quote/RELIANCE`
  - `GET /api/v1/market/history/TCS?days=30`
  - `GET /api/v1/market/fundamentals/INFY`

**IMPORTANT:** Phase 3 purely exposes read-only market data logic. It does **not** evaluate investments, generate signals, or place trades.

## Analysis Architecture (Phase 4)
The Investment Analysis Engine synthesizes market data into explainable, deterministic analysis reports.

- **Analyzers**: Includes modular components (`FundamentalAnalyzer`, `TechnicalAnalyzer`, `ValuationAnalyzer`, `QualityAnalyzer`, `RiskAnalyzer`).
- **Asset Specificity**: Tailors the components to the `AssetType` (Stocks vs. ETFs vs. Mutual Funds). For example, mutual funds skip stock-specific fundamentals.
- **Score Normalization**: Evaluates a final `long_term_suitability_score` from 0-100 by calculating a weighted average of *only available data*.
- **Missing Data Handling**: Properly records missing metrics in the `missing_data` field without fabricating scores.
- **Explainability**: Every report contains descriptive textual arrays for `strengths`, `risks`, and a final `explanation`. 
- **Confidence Metrics**: Reports include `analysis_confidence` (e.g., HIGH, MEDIUM, LOW) based on data completeness.
- **API Examples**:
  - `GET /api/v1/analysis/stock/RELIANCE`
  - `GET /api/v1/analysis/etf/NIFTYBEES`
  - `GET /api/v1/analysis/mutual-fund/MF123`
  - `GET /api/v1/analysis/{asset_type}/{symbol}`

**IMPORTANT DISCLAIMER:** The analysis score is not a prediction of future returns. The engine calculates historical risk and suitability structurally; it does not issue autonomous BUY or SELL decisions or call out to any AI models/LLMs.

## Capital Allocation Engine (Phase 5)
The Capital Allocation Engine computes theoretical allocations over suitable investments based on cash, risk profiles, diversification boundaries, and capital size.

- **Portfolio Analyzer**: Summarizes portfolio invested value, cash value, overall metrics.
- **Diversification Engine**: Bounds single-stock and single-asset percentage exposure using user-defined `RiskProfile` mappings.
- **Position Sizing Engine**: Floors target allocations mathematically using `Decimal` strictly, mapping fractional capabilities only where the asset class allows (e.g., Mutual Funds vs. entire Stock quantities).
- **Cash Reserve**: Respects a global minimum unallocated cash buffer configurable via the risk profile.
- **API Examples**:
  - `POST /api/v1/portfolio/{id}/allocation-preview`

**IMPORTANT DISCLAIMER:** Phase 5 purely produces an `AllocationRecommendation`. It explicitly does **not** evaluate live executions, and does **not** trigger any paper or live broker APIs.

## AI Investment Decision Engine (Phase 6)
The AI Investment Decision Engine uses the structured outputs from Phase 4 and Phase 5 to produce an explainable investment recommendation.

- **AI Provider Abstraction**: A `MockAIProvider` validates the interaction architecture without calling actual models during tests. Implementations like `GeminiAIProvider` can be plugged in using environment variables.
- **Allowed Decisions**: `BUY`, `HOLD`, `ADD`, `REDUCE`, `SELL`, `AVOID`.
- **JSON Validation**: Enforces strict Pydantic parsing of AI responses ensuring proper schemas and logical thresholds.
- **Business Guardrails**: Overrides AI hallucination or illogical outputs (e.g. failing to recommend a `BUY` if the safety guardrail overrides it due to INSUFFICIENT confidence or VERY HIGH risk).
- **Audit Persistence**: Every decision is stored systematically inside the `DecisionRecord` for traceability (with prompt versions, reasons, etc).
- **API Endpoints**:
  - `POST /api/v1/decision/preview` (Generates decision)
  - `GET /api/v1/decision/{id}` (Retrieves decision audit)

**IMPORTANT DISCLAIMER:** Phase 6 generates investment recommendations only. It does not execute trades. The AI does not directly connect to brokers or the PaperBroker execution mechanism.

## Risk & Safety Approval Engine (Phase 7)
The Risk Engine sits between the AI Decision Engine and any future Execution Engine to act as the final safety gate. It strictly enforces deterministic business logic that the AI cannot override.

- **Delivery-Only Policy**: All stock and ETF equity purchases enforce an explicit `DELIVERY_LONG_TERM` intent.
- **Capital Protection**: Validates that orders do not exceed available cash.
- **Concentration Limits**: Imposes maximum single-asset limits based on the user's risk profile (e.g. max 10% for a MODERATE profile). It dynamically modifies or rejects amounts exceeding limits.
- **Data Freshness**: Rejects BUY/ADD decisions if quote data is considered stale.
- **AI Override Protection**: The Risk Engine takes priority and forces rejections over AI recommendations if any fundamental safety condition fails (e.g., negative amounts, intraday intents, or invalid prices).
- **Execution Separation**: The engine does NOT invoke `PaperBroker` or any execution interface. It strictly produces a structured `RiskApprovalResult`.
- **Audit Logging**: Approval and rejection flows persist safely into `RiskApprovalRecord`.

**"This system is designed for long-term delivery investing. It does not support intraday trading, margin trading, leverage, short selling, or F&O trading."**

## Current Limitations
- Phase 1-7 do NOT implement live broker APIs or real autonomous trading execution.
- Trading execution is strictly limited to paper mechanisms (not connected to AI yet).
- Market data is currently deterministic mock data; real provider plugins will be attached in future phases.

## Autonomous Portfolio Management (Phase 8A)
Phase 8A completes the autonomous investment decision-to-paper-execution pipeline. It orchestrates the entire lifecycle of an investment cycle conceptually, enforcing strict safety rules without connecting to a real broker.

- **Market Session**: Checks if the market is open before allowing any equity execution.
- **Candidate Discovery**: Uses an `InvestmentUniverseProvider` to deterministically discover assets.
- **Autonomous Pipeline**: Integrates Market Data → Analysis → Allocation → AI Decision → Risk Approval → Paper Execution.
- **Capital Protection**: Recalculates available capital sequentially within a cycle to prevent allocating the same cash to multiple assets.
- **Idempotency**: Prevents executing the same AI decision multiple times.
- **Execution Limits**: Ensures strictly `DELIVERY_LONG_TERM` execution intents.

**IMPORTANT DISCLAIMER:** Phase 8A completes the autonomous pipeline but executes exclusively against a `PaperBroker`. It does not connect to a real broker.

## Phase 8B & 8C: Autonomous API & Hardening
Phase 8B introduces an extensive structural test suite to guarantee invariant safety. Phase 8C exposes the `AutonomousPortfolioManager` via a clean API layer for triggering and monitoring cycles.

- **Strict Configuration**: Controlled by `AUTONOMOUS_MODE`.
- **API Isolation**: All endpoints require authenticated user verification and explicitly enforce portfolio ownership boundaries. Users cannot trigger cycles or view executions for portfolios they do not own.
- **Reporting**: The API accurately exposes `PAPER` as the broker mode; live endpoints do not exist.

### `POST /api/v1/autonomous/cycle/{portfolio_id}`
Triggers exactly one autonomous portfolio-management cycle.
- **Requires**: Authenticated user & portfolio ownership.
- **Safety**: Requires `AUTONOMOUS_MODE=True`. Respects the `CYCLE_ALREADY_RUNNING` lock.

### `GET /api/v1/autonomous/cycle/{cycle_id}`
Returns details and summary for a given cycle.
- **Requires**: Authenticated user & portfolio ownership mapping.

### `GET /api/v1/autonomous/cycle/{cycle_id}/executions`
Returns execution records belonging to that cycle.
- **Requires**: Authenticated user & portfolio ownership mapping.

### `GET /api/v1/autonomous/status/{portfolio_id}`
Returns the current autonomous and broker status for the portfolio.
- **Requires**: Authenticated user & portfolio ownership mapping.
- **Returns**: `broker_mode: "PAPER"` strictly. Live broker mode is never exposed.

## Phase 9.1: Angel One SmartAPI Integration Foundation
Phase 9.1 introduces the foundational integration architecture for **Angel One**, the selected broker for the system.

- **Strictly Read-Only**: This phase implements authentication, mapping, and read-only synchronization (cash, holdings, orders). **No real orders are placed.**
- **Live Trading Guard**: A hardcoded `LiveBrokerExecutionGuard` strictly prevents order placement, regardless of configurations. `ENABLE_LIVE_TRADING` must remain `false`.
- **Environment Driven**: Authentication credentials (API Key, Client ID, Password, TOTP Secret) are strictly injected via `.env`. No secrets are logged, exposed, or committed.
- **Paper Broker Fallback**: `PaperBroker` remains the default system broker.
- **Long-Term Delivery Strategy**: The system strictly recognizes `DELIVERY` products. It explicitly filters out and ignores any holdings flagged as intraday, margin, or leverage.

## Phase 9.2: Broker Portfolio Reconciliation
Phase 9.2 introduces the reconciliation engine to detect differences between the broker's real state and the system's internal portfolio state.

- **Angel One remains read-only**: The system securely audits differences but NEVER places a broker order to correct them.
- **Reconciliation detects differences**: Compares cash balances, positions, quantities, and average prices. Highlights `BROKER_ONLY` or `INTERNAL_ONLY` anomalies.
- **No automatic corrective orders**: Misalignments are logged as `MISMATCH`, but the system will NOT automatically buy or sell assets to fix them.
- **No automatic liquidation**: If an internal holding is entirely missing from the broker, it is flagged as `CRITICAL` but never silently liquidated.
- **No live trading**: `LiveBrokerExecutionGuard` remains permanently active.
- **PaperBroker remains functional**: Local simulations continue unaffected.
- **Delivery-long-term only**: Broker holdings identified as intraday, leverage, or derivatives are explicitly flagged as `UNSUPPORTED_BROKER_POSITION` with `CRITICAL` severity and safely ignored.

## Phase 9.3: Broker Order Execution Foundation (Mock/Read-Only)
Phase 9.3 builds the foundational execution infrastructure to connect the portfolio management pipeline to a broker API using the `BrokerExecutionAdapter` interface.

- **Strictly Mocked / Read-Only**: The pipeline integrates with a deterministic `MockAngelOneExecutionAdapter`. **No live orders are placed.**
- **Robust State Machine**: Tracks orders through `CREATED`, `SUBMITTED`, `OPEN`, `PARTIALLY_FILLED`, `FILLED`, and `REJECTED`/`FAILED` states.
- **Idempotency**: Prevents duplicate submissions at the database level using a unique `client_order_id`.
- **Backward Compatibility**: Maintains the legacy `PaperBroker` and execution simulation behavior while bridging to the new robust models.
- **Live Execution Blocked**: Live trading is explicitly rejected by the engine logic (`LIVE_TRADING_DISABLED`) even if a real broker adapter is instantiated.


## Phase 9.4 ? Shadow Mode + Production Safety Hardening

This phase implements strict safety controls and simulated "Shadow Mode" execution, completely isolating the autonomous decision engine from real broker order placement.

### Execution Modes

* **PAPER**: Uses internal mock portfolio and order tracking. 
* **SHADOW**: Runs the complete autonomous decision engine (market data, analysis, allocation, risk) but executes internally via ShadowExecutionService and tracks simulated fills via ShadowOrderRecord.
* **LIVE**: Real broker execution via Angel One. **Currently strictly DISABLED by safety guards.**

### Safety Guards

* ENABLE_LIVE_TRADING = False
* LIVE_EXECUTION_UNLOCKED = False
* BROKER_EXECUTION_BLOCKED = True
* AUTONOMOUS_KILL_SWITCH = False

If any of these flags are overridden without proper authorization, the application will fail-closed on startup or immediately block execution.

### Shadow Performance

The shadow mode provides hypothetical P&L and metrics via ShadowPortfolioSimulator. **Note: Shadow performance is hypothetical and is NOT proof of future profitability.**



## Phase 9.5 ? Production Execution Readiness Gate

This phase establishes the final safety and readiness boundary before any hypothetical future live broker calls.

### Execution Readiness Pipeline

Before any order can be considered for execution, it must pass a strict ExecutionReadinessService that checks:

* **Authentication & Ownership**: Prevents cross-user or cross-portfolio execution.
* **Decision Freshness**: Rejects executions based on decisions older than DECISION_MAX_AGE_SECONDS.
* **Risk Approval Freshness**: Rejects if the risk approval is older than RISK_APPROVAL_MAX_AGE_SECONDS.
* **Reconciliation Safety**: Hard-blocks if any CRITICAL or UNSUPPORTED_BROKER_POSITION issues exist. Trading cannot be used to auto-resolve reconciliation bugs.
* **Analysis Coverage**: Requires a minimum confidence threshold for STOCK BUY/ADD decisions to ensure sufficient fundamental/technical diligence.
* **Market Data Freshness**: Validates that market data quotes are not stale.
* **Idempotency**: Prevents duplicate executions by validating against already completed simulated (or future real) shadow orders.
* **Cash & Holdings**: Simulates allocation to ensure it respects the cash reserve limits and holdings availability.
* **Intent**: Enforces DELIVERY_LONG_TERM.

### Live Trading Remains Disabled

ENABLE_LIVE_TRADING and LIVE_EXECUTION_UNLOCKED must remain set to False. The system remains read-only to Angel One.



## Phase 9.6 ? Broker Connectivity, Session Reliability & Operational Monitoring

This phase introduces robust broker connection tracking to ensure any data derived from Angel One is stable and verifiable. **LIVE execution remains fully disabled.**

### Key Components

* **Broker Session Manager**: Tracks the status of AngelOneSessionManager across states (DISCONNECTED, CONNECTING, CONNECTED, EXPIRED, RECONNECTING, FAILED, BLOCKED). Secret handling is strictly enforced with zero logging.
* **Broker Health Service**: Centralized BrokerHealthStatus monitor for tracking latencies, continuous failures, rate limit events, and auth failures.
* **Circuit Breaker**: Implementing a generic fallback wrapper. If the threshold of concurrent API failures triggers, it transitions from CLOSED to OPEN to prevent cascading failures.
* **Safe Retries & Rate-Limit Handling**: Rate-limits gracefully backoff. Retries are tightly bounded to prevent endless recursive API loops.
* **Data Freshness & Broker Snapshots**: Identifies data staleness independently for cash, holdings, positions, orders, and quotes. Broker state is tracked immutably in BrokerSnapshot.

### Safety Enhancements
* A failed request no longer falsifies data into zero constraints. Failed components mark statuses strictly to UNAVAILABLE.
* Reconciliation blocks execution cleanly with RECONCILIATION_BLOCKED_DATA_UNAVAILABLE rather than misleadingly approving when data defaults are missing.



## Phase 9.7 ? Autonomous Investment Decision Quality & Portfolio Protection Hardening

This phase hardens the AI evaluation lifecycle, stripping the AI of any ability to override deterministic, safety, or valuation checks independently.

### Analytical Improvements
* **Fundamental Strictness**: Explicit checks added.
* **Technical Constraints**: Validates long term trends.
* **Valuation & Quality**: Independent evaluations.
* **Confidence Constraints**: Incomplete analysis degrades confidence. INSUFFICIENT blocks BUY.

### Safety Enhancements
* **Hallucination Blocks**: Over-allocations are squashed securely.
* **Live Orders Block**: Verified.


## PHASE 10 ? FINAL AUDIT & PRODUCTION READINESS (COMPLETE)
The system has undergone a complete static code audit, security review, and end-to-end testing protocol.
- **Total Tests**: 105/105 Passing.
- **Safety Status**: ENABLE_LIVE_TRADING and LIVE_EXECUTION_UNLOCKED remain permanently set to False. The system is in a strict Shadow/Paper execution mode. 
- **Real Executions**: ZERO real orders were placed during the lifetime of this project's development.
- **Live Trading Authorization**: Live trading is explicitly disabled. The application is strictly read-only for Angel One and relies on deterministic guardrails to manage shadow allocations.

### Limitations & Disclaimer
This system is an autonomous analysis and shadow-execution platform. It cannot guarantee profit and is not immune to market risk. The system operates strictly for Long-Term Delivery investing and does not support Intraday, Options, Futures, Margin, or Short Selling.


## PHASE 10 (Revision 3) ? FINAL HUMAN-APPROVED LIVE DELIVERY TRADING
The system has verified the explicit human-approval execution paths.
- **Human Approval Only**: The system strictly limits real-money execution through human-in-the-loop preview and confirmation stages.
- **Safety**: Unattended real-money trading is disabled natively and programmatically via LiveBrokerExecutionGuard.
- **E2E Validation**: The small capital ?500 constraints successfully simulate and safely guard against fractional equity allocations and insufficient cash constraints.
- **Analysis Enhancements**: All fundamental and technical algorithms strictly prioritize missing data penalization over AI hallucination.
