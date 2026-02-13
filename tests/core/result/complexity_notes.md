# Complexity Notes - Unit Test Review

## Overview

All functions in `core/utils.py` and `core/remote_manager.py` were unit tested.
No functions were skipped entirely — however, the following functions showed
elevated complexity that warrants future refactoring.

---

## Functions with Complexity Concerns

### 1. `core.utils.get_transaction_history()`

**Severity: HIGH**

- **Cyclomatic complexity**: Multiple nested loops with nested try/except
- **Bare excepts**: Two levels of `except: continue` silently swallow all errors
- **Mixed responsibilities**: File discovery, line parsing, and field extraction
  are all in one function
- **Recommendation**: Split into three helpers:
  - `_find_log_files(log_dir) -> list[str]`
  - `_parse_log_line(line: str) -> dict | None`
  - `get_transaction_history()` as the orchestrator calling the above
- **Test status**: Tested (6 tests), but edge cases around malformed lines are
  hard to verify because errors are silently swallowed

### 2. `core.remote_manager.update_status()`

**Severity: MEDIUM**
v
- **Parameter count**: 6 parameters (phase, details, balance, portfolio,
  open_orders, high_water_marks)
- **Read-modify-write**: Reads existing state, merges with new values, writes
  back. Each `None` parameter triggers a fallback to previously persisted data.
- **Hidden coupling**: Behavior depends on file content from previous calls
- **Recommendation**: Extract merge logic into `_merge_state(current, updates)`
  and keep `update_status()` as a thin write wrapper
- **Test status**: Fully tested (8 tests), including merge/preserve behavior

---

## Functions That Were Clean and Easy to Test

| Function | Module | Verdict |
|---|---|---|
| `clean_amount()` | utils | Pure function, no side effects, 15 tests |
| `calculate_fee()` | utils | Pure function, clear math, 8 tests |
| `extract_json_list()` | utils | Pure function, 10 tests |
| `print_analysis_summary()` | utils | Output-only, 7 tests via capsys |
| `log_success()` | utils | File I/O, simple append, 6 tests |
| `get_todays_log_content()` | utils | File read, 3 tests |
| `load_blacklist()` | utils | File read with fallbacks, 4 tests |
| `save_blacklist()` | utils | File write, 2 tests |
| `add_to_blacklist()` | utils | Combines load+save, 4 tests |
| `_ensure_json_dir()` | remote_manager | Idempotent dir creation, 2 tests |
| `get_command()` / `set_command()` | remote_manager | Simple JSON read/write, 5 tests |
| `get_state()` | remote_manager | JSON read with defaults, 3 tests |
| `get_high_water_marks()` | remote_manager | Thin wrapper over get_state, 1 test |
| `save_high_water_marks()` | remote_manager | Read-modify-write, 5 tests |
| `get_live_logs()` | remote_manager | Tail-read with deque, 5 tests |
