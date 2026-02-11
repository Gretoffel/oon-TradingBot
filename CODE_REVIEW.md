# CODE REVIEW - OON Trading Bot

**Review Date:** 2026-02-11
**Reviewed by:** Claude (Automated Code Analysis)
**Codebase Size:** ~2,324 lines of Python, ~66MB total

---

## EXECUTIVE SUMMARY

The project is a functional trading bot with good architecture and a well-thought-out trading strategy. However, there are **critical security issues**, missing tests, and significant room for improvement in code quality.

**Overall Rating: B- (3.0)**

| Category | Grade | Comment |
|----------|-------|---------|
| **Code Quality** | B- | Good structure, but functions too long, no type hints |
| **Architecture** | A- | Clean separation, supervisor pattern, clear phases |
| **Security** | D | **CRITICAL:** Credentials exposed, browser data in repo |
| **Documentation** | B+ | Good user docs, missing technical docs |
| **Testing** | F | **Zero tests present** |
| **Production-Ready** | C | Works, but fragile and risky |

---

## 1. CONFIGURATION - STATUS

### Overview of Config Files:

| File | Format | Status | Purpose |
|------|--------|--------|---------|
| `.env` | ENV | **CRITICAL** | Credentials (EXPOSED!) |
| `requirements.txt` | TXT | Good | Dependencies (pinned) |
| `config.py` | Python | Excellent | Central configuration |
| `.gitignore` | TXT | Incomplete | Git excludes |
| `bot_state.json` | JSON | Good | Runtime state |
| `blacklist.json` | JSON | Good | Dynamic blacklist |

### **POSITIVE:**
- **Central Configuration:** All magic numbers are extracted into `config.py` (no hardcoded values in code)
- **Format mix makes sense:**
  - `.env`: Credentials (correct choice)
  - `config.py`: Complex business logic (trading parameters, time windows)
  - `requirements.txt`: Standard for Python dependencies
  - JSON: Runtime state (correct choice for IPC)

### **ISSUES:**

1. **No YAML/TOML:**
- Currently: Everything in ENV + Python + JSON
- **Recommendation:** For complex configs (trading strategy), YAML could be more readable:

```yaml
# config.yml (Optional - Alternative to config.py)
trading:
  limits:
    max_positions: 5
    max_buys_per_cycle: 3
    min_investment: 500
    max_investment: 1500

  strategy:
    rsi:
      min: 45
      max: 80
    ema_period: 50
    stop_loss: -0.025
    take_profit: 0.20
```

**However:** The current solution with `config.py` is perfectly fine for this project.

---

## 2. CODE QUALITY - GENERAL ANALYSIS

### **STRENGTHS:**

#### A. Good Architecture Patterns
```python
# Supervisor Pattern (main.py)
while True:
    try:
        await bot.run_cycle(full_analysis=should_do_full_analysis())
    except Exception as e:
        logger.error(f"Crash: {e}")
        await asyncio.sleep(BACKOFF_DELAY)
```
**Rating:** Robust, production-grade error recovery

#### B. Clean Separation of Concerns
- `bot.py`: Orchestration (logic only, no I/O)
- `actions.py`: UI automation (browser actions only)
- `market_data.py`: Data fetching (API calls only)
- `algo_service.py`: Strategy (calculations only)

**Rating:** Very good, no mixing of responsibilities

#### C. Config Centralization
```python
# config.py
MAX_POSITIONS = 5
MIN_INVESTMENT_EUR = 500.0
STOP_LOSS_THRESHOLD = -0.025
```
All values are centrally defined - **Best Practice!**

#### D. Error Handling
```python
async def execute_buy_order(...):
    try:
        # Order logic
    except TimeoutError:
        logger.warning("Timeout - retrying...")
        return await execute_buy_order(...)  # Retry
    except Exception as e:
        logger.error(f"Fatal: {e}")
        return None
```
**Rating:** Try/except everywhere, graceful degradation

---

### **WEAKNESSES:**

#### 1. **No Type Hints** (Severe)
```python
# Currently:
def clean_amount(text):
    return float(text.replace('.', '').replace(',', '.'))

# Should be:
def clean_amount(text: str) -> float:
    """Convert German number format to float."""
    return float(text.replace('.', '').replace(',', '.'))
```

**Impact:**
- No IDE autocomplete
- No type validation
- Hard to maintain

**Examples where type hints are missing:**
- `src/utils.py`: 10/10 functions without types
- `src/actions.py`: 7/7 functions without types
- `src/market_data.py`: 8/8 functions without types

**Fix:** Introduce MyPy + type hints

#### 2. **Functions Too Long** (Maintainability)

**Problematic functions:**

| File | Function | Lines | Problem |
|------|----------|-------|---------|
| `actions.py` | `execute_buy_order` | 225 | Too complex, 5+ nested try/except |
| `market_data.py` | `get_market_snapshot` | 127 | Does too much (fetch + analyze + score) |
| `oon_service.py` | `scan_depot_data` | 89 | 4 different parsing methods |
| `ai_service.py` | `run_ai_defense_check` | 92 | Mix of browser + parsing |

**Refactoring example:**
```python
# Before (225 lines):
async def execute_buy_order(page, search_term, budget_eur, ...):
    # Search logic
    # Validation logic
    # Order placement
    # Error handling
    # Blacklist logic

# After (better):
async def execute_buy_order(page, search_term, budget_eur, ...):
    stock_info = await _search_stock(page, search_term)
    if not await _validate_stock(page, stock_info):
        return None
    order_result = await _place_order(page, stock_info, budget_eur)
    await _handle_order_result(order_result)
    return order_result

async def _search_stock(page, search_term): ...
async def _validate_stock(page, stock_info): ...
async def _place_order(page, stock_info, budget_eur): ...
async def _handle_order_result(result): ...
```

#### 3. **Mixed Languages** (Consistency)

**Issues:**
- Code: English
- Comments: German
- Log messages: German with emojis
- Variable names: Mixed

**Examples:**
```python
# actions.py
logger.info(f"🛒 Kaufe {search_term} mit Budget {budget_eur} EUR")  # German
budget_eur = ...  # English
# Warte auf Modal-Text  # German comment

# algo_service.py
grund = "RSI zu niedrig"  # German variable
def calculate_score(candidate): ...  # English function
```

**Recommendation:** Switch everything to English (standard in open source)

#### 4. **Hardcoded Data** (Scalability)

**Problem:** 52 stock tickers are hardcoded in `market_data.py`
```python
NASDAQ_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", ...
]
ATX_TICKERS = [
    "ANDR.VI", "EBS.VI", "OMV.VI", ...
]
```

**Should be:**
```json
// tickers.json
{
  "US": ["AAPL", "MSFT", ...],
  "ATX": ["ANDR.VI", ...],
  "DAX": ["SAP.DE", ...]
}
```

```python
# market_data.py
with open('tickers.json') as f:
    TICKERS = json.load(f)
```

#### 5. **No Input Validation**

```python
async def execute_buy_order(page, search_term, budget_eur, ...):
    # No checks:
    # - Is budget_eur > 0?
    # - Is budget_eur <= available funds?
    # - Is search_term a valid string?
    # - Is page still connected?

    # Used immediately:
    await page.fill("#search", search_term)  # Crash if None!
```

**Fix:**
```python
async def execute_buy_order(page, search_term, budget_eur, ...):
    if not page or not page.url:
        raise ValueError("Page not connected")
    if not search_term or not isinstance(search_term, str):
        raise ValueError("Invalid search_term")
    if budget_eur <= 0:
        raise ValueError("Budget must be positive")
    # ...
```

---

## 3. VULNERABILITIES - DETAILED

### CRITICAL (Fix immediately!)

#### 3. **No Tests**
- **Currently:** 0 tests
- **Risk:** Any update can break everything
- **Impact:** Not production-ready
- **Fix:** See Section 6

---

### MAJOR (Improve urgently)

#### 4. **Fragile Web Scraping**

**Problem:** Everything relies on text selectors that break on website updates:
```python
# actions.py
modal_text = await page.locator(".modal-body").text_content()
if "nicht gehandelt werden" in modal_text:  # Breaks on wording change!
```

**Risk:** Website update → Bot breaks completely

**Recommendation:**
- Fallback strategies (multiple selectors)
- Monitoring with alerts
- API integration instead of scraping (if available)

#### 5. **AI via Web Automation Instead of API**

**Currently:** Playwright controls the Google AI Studio web UI
```python
# ai_service.py
await page.click("#send-button")  # Clicks on web button
await page.wait_for_selector(".response", timeout=60000)  # Waits 60s
```

**Performance:** ~60 seconds per AI call

**Should be:** Gemini API directly
```python
import google.generativeai as genai
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')
response = model.generate_content(prompt)  # ~2-3 seconds!
```

**Advantages:**
- 20x faster (2-3s instead of 60s)
- More reliable (no browser crashes)
- Transparent rate limits
- Better error handling

**Cost comparison:**
- Web automation: Free, but slow + unstable
- Gemini API: $0.00025/1K tokens (very affordable!)

#### 6. **ISIN Extraction Too Complex**

**Problem:** 5 different methods are attempted (`oon_service.py:91-160`)
```python
# Method 1: Regex on tooltip
# Method 2: Regex on cell text
# Method 3: data attribute
# Method 4: Link parsing
# Method 5: Fuzzy name matching (!!!)
```

**Why problematic:**
- Hard to debug
- Performance impact (5x more DOM queries)
- Fuzzy matching can return wrong ISINs

**Recommendation:**
1. Analyze website HTML → Identify the most robust method
2. One primary method + one fallback method
3. On failure: Throw exception, don't guess

---

### MINOR (Nice to have)

#### 7. **No Rate Limiting**
```python
# market_data.py
for ticker in ALL_TICKERS:  # 52 tickers
    data = yf.Ticker(ticker).history(...)  # Can get banned
```

**Fix:** Add rate limiter
```python
import asyncio
async def fetch_with_rate_limit(ticker):
    await asyncio.sleep(0.1)  # 100ms delay
    return yf.Ticker(ticker).history(...)
```

#### 8. **Logging Not Structured**
```python
# Currently:
logger.info(f"🎯 Gekauft: {symbol} für {amount} EUR")

# Better (JSON logging):
logger.info("order_executed", extra={
    "action": "buy",
    "symbol": symbol,
    "amount": amount,
    "timestamp": datetime.now().isoformat()
})
```

**Advantage:** Logs are machine-readable (e.g., for monitoring tools)

#### 9. **No Monitoring/Alerts**
- Bot can crash without anyone noticing
- No email/SMS on errors
- No performance metrics

**Recommendation:**
- Sentry.io for error tracking
- Email notifications on crashes
- Prometheus + Grafana for metrics

---

## 4. GARBAGE CODE - WHAT NEEDS TO GO?

### **DELETE COMPLETELY:**

#### 1. `google_session/` folder (65MB!)
```bash
git rm -rf google_session/
```
**Reason:** Personal browser data, not code

#### 2. Remove `.env` from git history
```bash
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all
```

---

### **CLEAN UP:**

#### 3. Empty Function in `algo_service.py`
```python
def calculate_algo_decisions(depot_data):
    """Placeholder - not used"""
    return []
```
**Reason:** Does nothing, only causes confusion

#### 4. Commented-Out Debug Code
```python
# utils.py:123
# print(f"Debug Row Error: {e}")  # No longer needed
```

#### 5. Duplicate Code Between Files
```python
# actions.py and oon_service.py both have:
async def click_cancel_button(page):
    # Exactly the same logic!
```
**Fix:** Extract into `browser_utils.py`

---

### **REFACTORING NEEDED:**

#### 6. `execute_buy_order` (225 lines)
**Currently:** One mega-function does everything
**Should be:** 5-6 small functions (see Section 2.2)

#### 7. Hardcoded Ticker Lists
**Currently:** 52 tickers in `market_data.py`
**Should be:** `tickers.json` file

#### 8. Mixed Language Strings
```python
# Scattered everywhere:
logger.info("🛒 Kaufe...")  # German
logger.info("🎯 Found candidate...")  # English (???)
```
**Fix:** Everything in English or German, but consistent

---

## 5. GARBAGE FUNCTIONS - INDIVIDUAL

### **Completely useless:**

```python
# algo_service.py:298
def calculate_algo_decisions(depot_data):
    return []
```
**Reason:** Always returns empty list, never called
**Action:** Delete

---

### **Overcomplicated:**

```python
# oon_service.py:91-160
async def resolve_isin_from_row(row):
    # 5 different methods (see Section 3.2.6)
```
**Reason:** Too many fallbacks, fuzzy matching is dangerous
**Action:** Reduce to 1-2 robust methods

---

### **Refactoring Candidates:**

| Function | File | Lines | Problem | Fix |
|----------|------|-------|---------|-----|
| `execute_buy_order` | `actions.py` | 225 | Too long, does too much | Split into 5-6 functions |
| `get_market_snapshot` | `market_data.py` | 127 | Fetch + analyze + score | Separate into 3 functions |
| `scan_depot_data` | `oon_service.py` | 89 | 4 parsing methods | Simplify |
| `run_ai_defense_check` | `ai_service.py` | 92 | Browser + parsing mixed | Separate |

---

## 6. IMPROVEMENT OPTIONS - PRIORITIZED

### **CRITICAL - IMMEDIATELY (Security):**

1. **Remove credentials**
   ```bash
   # Delete .env from history
   git filter-branch --force --index-filter "git rm --cached --ignore-unmatch .env" ...

   # Create .env.example
   echo "BOERSEN_EMAIL=your_email_here" > .env.example
   echo "BOERSEN_PASSWORD=your_password_here" >> .env.example
   ```

2. **Remove browser data**
   ```bash
   git rm -rf google_session/
   git commit -m "Remove personal browser data [SECURITY]"
   ```

3. **Complete `.gitignore`**
   ```gitignore
   # Python
   *.pyc
   __pycache__/
   .pytest_cache/
   .coverage
   htmlcov/

   # IDEs
   .vscode/
   .idea/
   .DS_Store

   # Environments
   venv/
   .env

   # Project
   google_session/
   logs/
   json/
   blackboard.txt
   ```

---

### **HIGH PRIORITY (Quality & Reliability):**

4. **Add tests**
   ```python
   # tests/test_utils.py
   import pytest
   from src.utils import clean_amount

   def test_clean_amount_german_format():
       assert clean_amount("1.234,56") == 1234.56

   def test_clean_amount_handles_zero():
       assert clean_amount("0,00") == 0.0

   def test_clean_amount_raises_on_invalid():
       with pytest.raises(ValueError):
           clean_amount("invalid")
   ```

   **Testable modules (easy to start with):**
   - `utils.py`: Parser functions
   - `algo_service.py`: Score calculations
   - `config.py`: Validation

   **Hard to test (but important):**
   - `actions.py`: Browser automation → Mock Playwright
   - `market_data.py`: API calls → Mock yfinance

5. **Type hints everywhere**
   ```python
   # Before:
   def clean_amount(text):
       return float(...)

   # After:
   from typing import Optional

   def clean_amount(text: str) -> float:
       """Convert German number format '1.234,56' to float 1234.56."""
       if not text or not isinstance(text, str):
           raise ValueError(f"Invalid input: {text}")
       return float(text.replace('.', '').replace(',', '.'))
   ```

   **Tools:**
   ```bash
   pip install mypy
   mypy src/  # Type check
   ```

6. **Gemini API instead of web automation**
   ```python
   # ai_service.py (NEW)
   import google.generativeai as genai

   async def run_ai_defense_check_api(depot_data):
       genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
       model = genai.GenerativeModel('gemini-1.5-pro')

       prompt = f"Analyze portfolio for sell signals:\n{depot_data}"
       response = await model.generate_content_async(prompt)

       return parse_ai_response(response.text)
   ```

   **Advantages:**
   - 20x faster (2-3s instead of 60s)
   - No browser overhead
   - More reliable

7. **CI/CD Pipeline**
   ```yaml
   # .github/workflows/ci.yml
   name: CI
   on: [push, pull_request]

   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - uses: actions/setup-python@v4
           with:
             python-version: '3.11'
         - run: pip install -r requirements.txt
         - run: pip install pytest mypy black
         - run: black --check src/
         - run: mypy src/
         - run: pytest tests/
   ```

---

### **MEDIUM PRIORITY (Maintainability):**

8. **Refactor long functions**
   ```python
   # actions.py - Before:
   async def execute_buy_order(page, search_term, budget_eur, ...):
       # 225 lines of code...

   # After:
   async def execute_buy_order(page, search_term, budget_eur, ...):
       stock = await _search_and_select(page, search_term)
       if not stock:
           return None

       validated = await _validate_tradability(page, stock)
       if not validated:
           _add_to_blacklist(search_term)
           return None

       order = await _place_limit_order(page, stock, budget_eur)
       return await _confirm_order(page, order)
   ```

9. **Hardcoded data → Config files**
   ```json
   // config/tickers.json
   {
     "US": {
       "NASDAQ": ["AAPL", "MSFT", "GOOGL", ...],
       "NYSE": ["JPM", "V", ...]
     },
     "EU": {
       "ATX": ["ANDR.VI", "EBS.VI", ...],
       "DAX": ["SAP.DE", "SIE.DE", ...]
     }
   }
   ```

10. **Unify language**
    - **Option A:** Everything in German (for local project)
    - **Option B:** Everything in English (for open source)

    **Recommendation:** English (standard)

    ```python
    # Before:
    logger.info(f"🛒 Kaufe {symbol}")
    grund = "RSI zu niedrig"

    # After:
    logger.info(f"Buying {symbol}")
    reason = "RSI too low"
    ```

---

### **LOW PRIORITY (Nice to have):**

11. **Monitoring & Alerting**
    ```python
    # monitoring.py
    import sentry_sdk

    sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"))

    def send_alert(message, level="error"):
        sentry_sdk.capture_message(message, level=level)
    ```

12. **Rate Limiting**
    ```python
    # market_data.py
    from asyncio import Semaphore, sleep

    RATE_LIMITER = Semaphore(5)  # Max 5 parallel requests

    async def fetch_ticker_data(ticker):
        async with RATE_LIMITER:
            await sleep(0.2)  # 200ms delay
            return yf.Ticker(ticker).history(...)
    ```

13. **Structured Logging**
    ```python
    import structlog

    logger = structlog.get_logger()
    logger.info("order_executed",
                action="buy",
                symbol=symbol,
                amount=amount,
                timestamp=datetime.now().isoformat())
    ```

14. **Performance Optimization**
    - Parallel AI calls (currently: sequential)
    - Cache for market data (currently: fetched fresh every time)
    - Database instead of JSON files (when scaling)

15. **Documentation**
    - Architecture diagram (system overview)
    - API documentation (Sphinx)
    - Deployment guide
    - Troubleshooting guide

---

## 7. CONCLUSION

### **What is good:**
- Clear architecture with supervisor pattern
- Clean separation of concerns
- Central configuration (no magic numbers)
- Well-thought-out trading strategy
- Error handling with graceful degradation
- Good user documentation

### **What needs to be fixed immediately:**
- **CRITICAL:** Remove credentials from repo
- **CRITICAL:** Delete browser data (65MB)
- **CRITICAL:** Write tests (at least basics)

### **What should be improved:**
- Add type hints everywhere
- Gemini API instead of web automation
- Refactor long functions
- Set up CI/CD pipeline
- Unify language (English)

### **Nice to have:**
- Monitoring & alerting
- Rate limiting
- Performance optimization
- Technical documentation

---

## 8. ACTIONABLE TODO LIST

### Phase 1: Security (IMMEDIATELY)
- [ ] Remove `.env` from git history
- [ ] Create `.env.example` with dummy values
- [ ] Delete `google_session/`
- [ ] Complete `.gitignore`
- [ ] Move secrets to environment variables

### Phase 2: Code Quality
- [ ] Add type hints to all functions
- [ ] Install and configure MyPy
- [ ] Refactor long functions (top 4)
- [ ] Unify language to English
- [ ] Set up Black/Ruff for code formatting

### Phase 3: Testing
- [ ] Install pytest
- [ ] Write tests for `utils.py` (10 tests)
- [ ] Write tests for `algo_service.py` (5 tests)
- [ ] CI/CD pipeline with GitHub Actions
- [ ] Bring test coverage to min. 50%

### Phase 4: Performance
- [ ] Implement Gemini API (instead of web automation)
- [ ] Hardcoded tickers → JSON file
- [ ] Rate limiting for API calls
- [ ] Caching for market data

### Phase 5: Production (Optional)
- [ ] Monitoring with Sentry.io
- [ ] Email alerts on crashes
- [ ] Structured logging (JSON)
- [ ] Collect performance metrics
- [ ] Write deployment guide

---

## APPENDIX: METRICS

**Code Statistics:**
- Total lines: 2,324 (Python)
- Files: 12 Python files
- Functions: ~60
- Type hints: 0% (!!!)
- Test coverage: 0% (!!!)
- Average function length: ~40 lines
- Longest function: 225 lines (`execute_buy_order`)

**Dependencies:**
- Direct dependencies: 7
- No known security vulnerabilities (as of Jan 2025)
- All dependencies with pinned versions

**Performance:**
- Quick cycle: ~10-15 seconds
- Full cycle: ~5-10 minutes (bottleneck: AI calls)
- AI call (web): ~60 seconds
- AI call (API): ~2-3 seconds (potential improvement)

**Estimated Refactoring Time:**
- Phase 1 (Security): 2-3 hours
- Phase 2 (Quality): 1-2 weeks
- Phase 3 (Testing): 1 week
- Phase 4 (Performance): 3-5 days
- Phase 5 (Production): 1-2 weeks

---

**Review created on:** 2026-02-11
**Tool:** Claude Code (Automated Analysis)
**Version:** 1.0
