# PROJECT FILE AUDIT

### A. REQUIRED_PRODUCTION
- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/services/market_data/angel_one.py`
- `backend/app/services/fundamentals/screener.py`
- `backend/app/services/execution/real_execution.py`
- `backend/app/services/execution/readiness.py`
- `backend/app/services/decision/decision_engine.py`

### B. REQUIRED_TEST
- `backend/tests/test_algo_execution_readiness.py`
- `backend/tests/test_angel_one_smoke.py`
- `backend/tests/test_real_execution.py`

### C. REQUIRED_DOCUMENTATION
- `FINAL_ARCHITECTURE.md`
- `FINAL_SAFETY_MODEL.md`
- `FINAL_DATA_SOURCES.md`
- `FINAL_DECISION_RULES.md`
- `FINAL_SETUP.md`
- `REAL_EXECUTION_ARCHITECTURE.md`
- `REAL_EXECUTION_SAFETY.md`
- `ORDER_CONFIRMATION_FLOW.md`
- `REAL_EXECUTION_SETUP.md`
- `REAL_EXECUTION_LIMITATIONS.md`
- `FINAL_AUDIT_REPORT.md`

### D. REQUIRED_CONFIGURATION
- `backend/.env.example`
- `.gitignore`
- `backend/pytest.ini`

### E. TEMPORARY/DEBUG (Moved to Archive)
- `backend/diagnostic_*.py`
- `backend/scratch_*.py`

### G. OBSOLETE (Moved to Archive)
- `backend/app/services/fundamentals/fmp.py`
- `backend/app/services/fundamentals/indian_api.py`
- `backend/app/services/fundamentals/eodhd.py`

### I. GENERATED/CACHE (Deleted)
- `backend/__pycache__/`
- `frontend/__pycache__/`
- `backend/.pytest_cache/`
- `.pytest_cache/`
- `test.db`
- `backend/test.db`
- `backend/local_dev.db`
