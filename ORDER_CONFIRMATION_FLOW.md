# ORDER CONFIRMATION FLOW

The user must manually confirm all AI-generated trades before they become live Angel One orders.

## Workflow

1. **AI Generation**: The Decision Engine ranks candidates, applies sizing logic, checks live cash limits, and generates an `OrderIntent`.
2. **Preview State**: The execution layer converts this into an `OrderPreview`. It locks the expected cash, holdings, and the live market price at the moment of intent generation.
3. **User Confirmation**: The UI polls for pending `OrderPreview` items. The user securely reviews:
   - Reasons and fundamental/technical metrics.
   - Quantity, estimated value, and remaining cash.
   - Any main risks.
   Once comfortable, the user explicitly authorizes via their authenticated session, creating an `OrderConfirmation`.
4. **Final Engine Validation**: Before hitting the broker, the system re-validates:
   - Does the user have enough cash RIGHT NOW?
   - Has the market price moved more than 2% since the preview?
   - Is this a duplicate order (within 60s)?
5. **Execution**: If passing all checks, it's submitted via `placeOrder` to the Angel One SmartAPI.
