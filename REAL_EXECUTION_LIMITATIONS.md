# REAL EXECUTION LIMITATIONS

1. **Unattended Trading**: Completely unsupported by design. If you leave the system running overnight, it will queue previews. If they expire before you wake up to confirm them, they will be discarded.
2. **Intraday & Leverage**: The engine strictly enforces `DELIVERY`. You cannot override this to do F&O or margin trading.
3. **Session Replay Attacks**: The execution engine assumes the caller providing `OrderConfirmation` has already authenticated the user. Session tokens and MFA mechanisms must be enforced at the API border.
4. **Broker-side Cancellations**: If Angel One accepts the order but later cancels it (due to margin shortfall, liquidity limits, or post-submission rejection), the system will mark it `RECONCILIATION_REQUIRED` and will **NOT** retry automatically.
