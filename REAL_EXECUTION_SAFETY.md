# REAL EXECUTION SAFETY LIMITS

1. **Mandatory Human Confirmation**: No order is submitted without an explicit confirmation ID mapped to the generated preview.
2. **Data Staleness & Price Change**: If the Angel One Live LTP deviates > 2% from the preview's locked LTP, the confirmation becomes immediately invalid.
3. **Product Type**: All orders are hardcoded to `DELIVERY`. Intraday and Margin trades are forcibly blocked by the engine.
4. **Duplicate Protection**: Any intent matching a similar intent submitted in the last 60 seconds is rejected.
5. **Cash Preservation**: Orders violating the `MIN_CASH_RESERVE` constraint will be blocked.
6. **Kill Switch**: `AUTONOMOUS_KILL_SWITCH = True` will override any valid confirmation and fail the execution.
