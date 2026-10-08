# REAL EXECUTION ARCHITECTURE

The execution layer operates under a strict state machine designed for mandatory human-in-the-loop validation.

## State Machine:
`SHADOW` -> `READY_FOR_CONFIRMATION` -> `CONFIRMED` -> `SUBMITTED` -> `EXECUTED`

## The Pipeline
1. **Decision Engine**: Generates BUY/SELL recommendations.
2. **Execution Readiness Layer**: Validates safety constraints and creates an `OrderIntent`.
3. **Real Execution Engine**: 
   - Translates `OrderIntent` into an `OrderPreview` (locking current market LTP and cash availability).
   - Pauses until the `OrderPreview` receives a signed `OrderConfirmation` from the authenticated user.
   - On confirmation, runs final pre-submission validations (duplicate check, expiry, material price change).
   - Submits to Angel One SmartAPI and enters `SUBMITTED`.
4. **Reconciliation**: A separate polling mechanism verifies Angel One order book to transition to `EXECUTED`, `REJECTED`, or `CANCELLED`.
