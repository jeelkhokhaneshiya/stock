# FINAL SAFETY MODEL

The safety model ensures that the system is entirely autonomous in its decision logic but remains completely isolated from live order placement.

## Core Safety Invariants
1. **No Live Execution**: Hardcoded logic drops any `OrderIntent` and prevents forwarding to the Angel One SmartAPI `placeOrder` endpoint.
2. **Read-Only Enforced**: 
   - `ENABLE_LIVE_TRADING=false`
   - `BROKER_EXECUTION_BLOCKED=true`
   - `LIVE_EXECUTION_UNLOCKED=false`
3. **Graceful Degradation**: Any failure to fetch market data or fundamental data correctly degrades the decision logic to `WATCH` or `NO_ACTION`.
4. **No Fake Data**: The engine strictly consumes real production data. No mock overrides exist in the production path.
5. **Loss-Aware Logic**: The system will not automatically SELL a losing position. A broken fundamental thesis is required to exit.
6. **Cash Constraints**: BUY and BUY_MORE decisions mathematically verify affordability against live Angel One cash balances.
