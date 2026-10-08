# FUNDAMENTAL PROVIDER DISCOVERY

**Date:** 2026-10-07
**Objective:** Identify one REAL, RELIABLE, and VERIFIED API provider for Indian (NSE) company fundamentals.
**Status:** DISCOVERY PHASE (No Integration Yet)

---

## 1. Candidate: Financial Modeling Prep (FMP)

**Official documentation:** [FMP API Docs](https://financialmodelingprep.com/developer/docs/)
**Indian/NSE coverage:** Excellent (supports `.NS` suffix, e.g., `HEROMOTOCO.NS`).
**ISIN support:** Yes. Provides `/search-isin?isin=` endpoint to map ISINs to exchange symbols.
**Financial statements:** Income statement, Balance sheet, Cash flow (Annual and Quarterly).
**Ratios & Profitability:** Comprehensive financial ratios, key metrics, and enterprise value.
**Shareholding:** Institutional ownership data available.
**API authentication:** Query parameter `?apikey=` or Header.
**Free/paid requirement:** Freemium. 250 requests/day free, BUT international markets (like NSE) strictly require the **Ultimate Plan**.
**Rate limits:** Depending on the tier, typically 300 to 1000 requests/minute on paid plans.
**Usability with current credentials:** UNUSABLE. We do not currently have an FMP Ultimate Plan API key in `.env`.

**Pros:**
- Enterprise-grade reliability and mathematical accuracy.
- Explicit ISIN-to-Symbol mapping.
- Very clean, standardized JSON responses.

**Cons:**
- Global data (India) is locked behind their most expensive tier.

**Exact Next Validation Step:**
1. Secure an Ultimate Plan FMP API key and add `FMP_API_KEY` to `.env`.
2. Test `/search-isin?isin=INE158A01026` to confirm ISIN resolution.
3. Test `/api/v3/income-statement/HEROMOTOCO.NS` to verify real NSE data payload.

---

## 2. Candidate: Finnhub

**Official documentation:** [Finnhub API Docs](https://finnhub.io/docs/api)
**Indian/NSE coverage:** Supported (via `exchange=NS` and `.NS` suffixes).
**ISIN support:** Supports `/search?q=ISIN` to resolve the ticker.
**Financial statements:** Basic financials, reported financials.
**Ratios & Profitability:** Margins, ROE, P/E available.
**Shareholding:** Institutional ownership provided.
**API authentication:** `X-Finnhub-Token` header or `?token=` query parameter.
**Free/paid requirement:** Freemium. 60 requests/minute free. Global fundamentals often require the **All-In-One paid plan**.
**Rate limits:** 60/min free, 300/min paid.
**Usability with current credentials:** UNUSABLE. We do not have a Finnhub API key.

**Pros:**
- Exceptional documentation and SDKs.
- Very fast response times.

**Cons:**
- Coverage for deep Indian fundamental history is sometimes sparse compared to US markets unless on premium tiers.

**Exact Next Validation Step:**
1. Obtain a Finnhub API key and add `FINNHUB_API_KEY` to `.env`.
2. Query `/stock/metric?symbol=HEROMOTOCO.NS&metric=all` to verify fundamental depth.
3. Assess if the free tier provides enough data or if the All-In-One plan is strictly required.

---

## 3. Candidate: RapidAPI - "Indian Stock Exchange API"

**Official documentation:** RapidAPI Hub (Provider: Indian Stock Exchange)
**Indian/NSE coverage:** Specifically designed for Indian markets (BSE/NSE).
**ISIN support:** Not natively supported; primarily relies on NSE symbol or BSE scrip codes.
**Financial statements:** Income statements, balance sheets, cash flows.
**Ratios & Profitability:** Financial ratios (liquidity, profitability, solvency).
**Shareholding:** Shareholding patterns available.
**API authentication:** `X-RapidAPI-Key` header.
**Free/paid requirement:** Freemium. Usually offers a small free testing quota (e.g., 50 calls/month).
**Rate limits:** Hard-capped by RapidAPI subscription tier.
**Usability with current credentials:** UNUSABLE. We do not have a configured RapidAPI key.

**Pros:**
- Dedicated strictly to the Indian market.
- Readily available on RapidAPI without complex enterprise onboarding.

**Cons:**
- Third-party aggregators on RapidAPI can suffer from unannounced downtime or breaking schema changes.
- Lack of native ISIN resolution means we must build a manual ISIN-to-Symbol cross-reference.

**Exact Next Validation Step:**
1. Obtain a RapidAPI key, subscribe to the specific API, and add `RAPIDAPI_KEY` to `.env`.
2. Test the `/financials` endpoint using `HEROMOTOCO` and `TCS` to verify payload structure.
3. Stress-test the endpoint for rate-limit headers to ensure safe throttling in the DecisionEngine.

---

## Conclusion & Recommendation

**Recommended Candidate:** **Financial Modeling Prep (FMP)**

**Why it is recommended:**
While it requires a paid Ultimate Plan to access Indian markets, FMP is the only provider that natively satisfies all your strict engineering requirements:
1. Native `ISIN` to `Symbol` mapping (eliminates identity mismatch risk).
2. Institutional-grade accuracy for derived metrics (no fabricated/stale values).
3. Uniform API schemas that fit perfectly into our existing `FundamentalDataProvider` abstraction.

*Important Note: Since no provider can be accessed safely and freely right now with the current `.env`, I am leaving production fundamentals BLOCKED as requested. We must not integrate any of these until a key is provisioned and the explicit validation script passes real data tests.*
