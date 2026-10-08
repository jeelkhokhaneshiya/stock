# FINAL DATA SOURCES

## Market Data
**Provider:** Angel One SmartAPI
- Used to pull real-time cash availability.
- Used to fetch actual holdings and open positions.
- Used to fetch last traded price (LTP).
- Transient errors handled securely without mocking.

## Fundamental Data
**Provider:** Screener.in
- Fully integrated as the primary provider.
- Extracts Revenue, EPS, P/E, ROE, ROCE, Debt/Equity, Book Value, Net Profit, and Shareholding.
- Automatically handles missing fields gracefully without defaulting to zero or fabricating values.
- Transient errors or HTTP timeouts mark data as `UNAVAILABLE` and securely downgrade any dependent decisions to `WATCH` or `NO_ACTION`.
