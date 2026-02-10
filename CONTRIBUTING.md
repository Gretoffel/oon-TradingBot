# Contributing to OÖN Trading Bot

First off, thanks for taking the time to contribute! 🎉

The following is a set of guidelines for contributing to the OÖN Trading Bot. These are mostly guidelines, not rules. Use your best judgment, and feel free to propose changes to this document in a pull request.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Coding Guidelines](#coding-guidelines)
- [Pull Request Process](#pull-request-process)

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide your environment details** (Python version, OS, etc.)
- **Include relevant log files** from `./logs/`
- **Add screenshots** if applicable

Create bug reports using the issue template: `[Text] Text`

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

- **Use a clear and descriptive title**
- **Provide a detailed description** of the suggested enhancement
- **Explain why this enhancement would be useful**
- **List any potential drawbacks or concerns**

### Your First Code Contribution

Unsure where to begin? Look for issues labeled:
- `good first issue` - Good for newcomers
- `help wanted` - Extra attention needed

### Pull Requests

1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. Ensure your code follows the project's coding style
4. Update documentation as needed
5. Make sure your code runs without errors

## Development Setup

1. **Clone your fork:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/oon-TradingBot.git
   cd oon-TradingBot
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   python -m playwright install
   
   # Install test dependencies
   pip install pytest pytest-asyncio pytest-cov
   ```

3. **Set up environment variables:**
   ```bash
   # Create .env file
   cp .env.example .env  # If you have a template, otherwise create it manually
   
   # Add your credentials:
   BOERSEN_EMAIL=your_email@example.com
   BOERSEN_PASSWORD=your_password
   ```

4. **Run tests to verify setup:**
   ```bash
   pytest
   ```

## Running Tests

### Quick Test Run
```bash
pytest                    # Run all tests
pytest tests/test_utils.py  # Run specific file
```

### With Coverage
```bash
pytest --cov=src --cov-report=html
# Open htmlcov/index.html to see coverage report
```

### Fast Tests Only (Skip Integration)
```bash
pytest -m "not integration"
```

**Important**: Always run tests before submitting a PR! Tests run automatically in CI, but catching issues early saves time.

## Coding Guidelines

### Style Basics

- **Python Version:** Use Python 3.8+
- **Async/Await:** Use async functions for all browser interactions
- **Imports:** Group standard library, third-party, and local imports separately
- **Docstrings:** Add docstrings to all public functions explaining their purpose

  (Not to serious)

### Key Practices

- **Error Handling:** Always wrap browser operations in try/except blocks
- **Logging:** Use descriptive print statements for debugging
- **Configuration:** Add new settings to `config.py`, not hardcoded
- **File Paths:** Use `os.path.join()` for cross-platform compatibility

### What NOT to do

- Don't commit `.env` files or credentials
- Don't bypass error handling for "quick fixes"
- Don't use `time.sleep()` - prefer `asyncio.sleep()` in async functions
- Don't commit large binary files or log files

## Pull Request Process

### Branch Naming

Always create your branch using one of these prefixes:

- `feature/*` - New features (e.g., `feature/add-dax-support`)
- `fix/*` - Bug fixes (e.g., `fix/isin-parsing-crash`)
- `chore/*` - Maintenance tasks (e.g., `chore/update-dependencies`)
- `enhancement/*` - Improvements to existing features (e.g., `enhancement/faster-scanning`)

**Example:**
```bash
git checkout -b feature/add-swing-trading-mode
```

### Submission Steps

1. **Run tests locally** - Make sure all tests pass:
   ```bash
   pytest
   ```
2. **Add tests for new features** - If you added functionality, add corresponding tests
3. **Update documentation** if you changed functionality
4. **Update `requirements.txt`** if you added dependencies
5. **Write a clear PR description:**
   - What problem does this solve?
   - How did you test it?
   - Any breaking changes?

6. **Wait for CI checks** - GitHub Actions will run tests automatically
7. **Wait for review** - maintainers will review your PR and may request changes
8. **Address feedback** - make requested changes and push to your branch
9. **Merge** - Once approved and tests pass, a maintainer will merge your PR

### PR Title Format

Use clear, descriptive titles:
- ✅ `Fix: Prevent crash when ISIN not found`
- ✅ `Feature: Add support for DAX stocks`
- ✅ `Docs: Update installation instructions`
- ❌ `fix stuff`
- ❌ `update`

## Questions?

Feel free to open an issue labeled `question` if you need help or clarification on anything!

---

**Thank you for contributing!** 🚀
