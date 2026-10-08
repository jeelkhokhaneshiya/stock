# FINAL LIMITATIONS

1. **Screener.in Rate Limits**: As Screener data is fetched via public endpoints, heavy bulk scraping or short-interval cycling will trigger rate limits or HTTP 403 blocks. The system mitigates this by handling failures gracefully and caching data safely.
2. **Missing Fundamental Data**: Screener.in may not have valid entries for obscure or newly listed tokens. The system will strictly mark these as `UNAVAILABLE` and avoid fabricated execution.
3. **Market Hours**: Angel One LTP and volume data relies on market hours. Out-of-hours testing might yield stale alerts, which naturally prevents buying until the data is fresh.
4. **Execution Bound**: Real execution cannot be triggered. Order Intents are generated purely for auditable tracing and paper/shadow testing.
