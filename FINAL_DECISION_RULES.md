# FINAL DECISION RULES

The Decision Engine strictly adheres to the following logic matrix to ensure risk-adjusted, cash-aware, and loss-aware recommendations:

## 1. Safety Checks
- Missing/Stale Market Data -> NO ACTION / WATCH
- Missing/Stale Fundamental Data -> NO ACTION / WATCH
- Zero Cash Available -> BUY blocked (WATCH)

## 2. Loss-Aware Holding Evaluation
If a holding is currently at a loss (PnL < 0):
- **THESIS_STRONG**: System will HOLD, or `BUY_MORE` if valuation is highly attractive and concentration < 10%.
- **THESIS_STABLE / UNCERTAIN**: System will HOLD and monitor closely.
- **THESIS_WEAK**: System will REDUCE exposure.
- **THESIS_BROKEN**: System will SELL to stop losses. (This is the ONLY path that triggers an automated loss exit).

## 3. Profit-Taking
If a holding is in profit (PnL > 0):
- **Concentration > 30%**: Triggers `REDUCE` to lock in profits and rebalance.
- **Valuation > Extremely Overvalued**: Triggers `REDUCE`.
- **THESIS_STRONG**: System will HOLD and let profits run, or `BUY_MORE` if cash is available and allocation is low.

## 4. Cash-Aware Sizing
- New `BUY` orders are dynamically sized based on available cash from Angel One.
- If calculated quantity is zero due to insufficient buffer or cash limits, the engine downgrades the decision to `WATCH`.
