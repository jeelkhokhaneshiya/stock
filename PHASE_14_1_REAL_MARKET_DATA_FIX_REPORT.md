# PHASE 14.1B — FIX ANGEL ONE TCS TOKEN RESOLUTION REPORT

## 1. Exact Root Cause
The previous token mapping logic inside `AngelOneMarketDataProvider._ensure_mapping()` applied a naive `.replace("-EQ", "")` operation across ALL elements within the Angel One `OpenAPIScripMaster.json` dump. Because this JSON contains tens of thousands of derivatives, options, and futures that might coincidentally contain or lack `-EQ`, this operation was too broad. Furthermore, because Python dictionaries sequentially overwrite identical keys, a later arbitrary derivative or alternate series record in the JSON could overwrite the canonical `NSE:TCS` equity entry, resulting in a blank or completely incorrect token during lookup, which subsequently manifested as `Skipping Angel One quote for TCS - could not resolve token`.

## 2. Actual TCS Master-List Record Characteristics
An investigation via script of the `OpenAPIScripMaster.json` showed exactly 387 total records containing `"TCS"`. 
The singular correct standard NSE Equity token record looks exactly like this:
```json
{
  "token": "11536",
  "symbol": "TCS-EQ",
  "name": "TCS",
  "expiry": "",
  "strike": "-1.000000",
  "lotsize": "1",
  "instrumenttype": "",
  "exch_seg": "NSE",
  "tick_size": "10.000000",
  "freeze_qty": "47035",
  "is_cas_enabled": true
}
```

## 3. Token-Resolution Fix
I implemented a strict, deterministic filtering algorithm inside `_ensure_mapping`:
- For NSE instruments, it now **strictly validates** that `symbol.endswith("-EQ")` AND `instrumenttype == ""`.
- It safely slices exactly the last 3 characters (`symbol[:-3]`) rather than running a global `replace`.
- For BSE instruments, it prevents accidental overwrites by enforcing a `if key not in self._master_mapping` check, thereby preserving the primary equity entry.

## 4. Tests Added
I updated the regression tests in `test_angel_one_quote.py` to include deterministic proofs for this logic:
- `test_mapping_resolves_exact_nse_equity`: Verifies only `TCS-EQ` resolves, ignoring `TCS24OCTFUT` and alternate series like `TCS-BE`.
- `test_mapping_bse_not_returned_for_nse`: Verifies `BSE` entries do not leak into `NSE` lookups.
- `test_mapping_ambiguous_fails_safely`: Verifies the first valid entry is kept if a duplicate is found.
- `test_no_hardcoded_token`: Verifies that clearing the map results in an empty response, proving there are no hidden/hardcoded string matches in the code.

## 5. Full Test Result
All 302 unit tests PASS (including the 12 strict token mapping and quote parsing rules).

## 6. Smoke-Test Result
```text
=== REAL-DATA SMOKE TEST ===
1. Angel One Authentication...
   PASS

2. Real Cash Test (RMS)...
   PASS: Available Cash: 101.7500

3. Real Holdings Test...
   PASS: Retrieved 2 holdings

4. Real Market-Data Test...
   PASS: Retrieved real quote for TCS (LTP: INR 2076.0)

5. Screener Real Fundamentals Test...
   PASS: Retrieved Screener data for TCS (PE: 13.7)
```
Status: **PASS**

## 7. Confirmation of Safety
- No real orders were placed.
- `LiveBrokerExecutionGuard` remains strictly active.
- No execution guards were bypassed.
- No dummy/mock prices were used. The `2076.0` LTP was dynamically fetched from the live Angel One SmartAPI using the correctly resolved `11536` token.
