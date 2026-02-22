# OON Trading Bot

![GitHub issues](https://img.shields.io/github/issues/Gretoffel/oon-TradingBot)
![GitHub PRs](https://img.shields.io/github/issues-pr/Gretoffel/oon-TradingBot)
![GitHub last commit](https://img.shields.io/github/last-commit/Gretoffel/oon-TradingBot)
![GitHub License](https://img.shields.io/github/license/Gretoffel/oon-TradingBot)

An automated trading bot for the [OON Boersespiel](https://www.oon-boersespiel.at) (OON Stock Market Game) using AI-powered decision making, technical analysis, and browser automation.

> [!IMPORTANT]
> This is a research/educational project for a stock market simulation game. Use at your own risk.

## Features

- **Multi-Phase Trading Loop** - 3-phase strategy: Defense (portfolio safety), Tech Scan (market data), Synthesis (AI + algo buy decisions)
- **Multiple AI Providers** - Google AI Studio (browser), OpenAI, Claude, Google Gemini API, Ollama (local)
- **Technical Analysis** - RSI, EMA, VWAP, ATR indicators via Yahoo Finance with momentum scoring
- **Smart Risk Management** - Stop-loss, take-profit, high water mark trailing stop, EOD protection
- **Live Dashboard** - Streamlit web UI with portfolio view, transaction history, and live console
- **Web Config** - Browser-based AI provider configuration page
- **Auto-Recovery** - Supervisor pattern with automatic restart on errors
- **Transaction Logging** - Daily log files with full trade details and AI reasoning

## Project Structure

```
oon-TradingBot/
├── src/
│   ├── main.py                  # Entry point & supervisor loop
│   ├── core/                    # Infrastructure
│   │   ├── config.py            # YAML config loader & constants
│   │   ├── utils.py             # Helpers (parsing, logging, blacklist)
│   │   └── remote_manager.py    # Bot state & control (JSON-based)
│   ├── trading/                 # Trading logic
│   │   ├── bot.py               # Main bot cycle orchestration
│   │   ├── actions.py           # Buy/sell order execution
│   │   ├── ai_service.py        # AI prompts (defense & deep-dive)
│   │   └── algo_service.py      # Portfolio safety & synthesis algorithm
│   ├── services/                # External services
│   │   ├── browser_utils.py     # Playwright browser context
│   │   ├── market_data.py       # Yahoo Finance data & technical indicators
│   │   └── oon_service.py       # OON website login & depot scanning
│   ├── ai_providers/            # AI provider implementations
│   │   ├── base_provider.py     # Abstract base class
│   │   ├── google_studio_provider.py
│   │   ├── google_api_provider.py
│   │   ├── openai_provider.py
│   │   ├── claude_provider.py
│   │   └── ollama_provider.py
│   └── ui/                      # Web interfaces
│       ├── dashboard.py         # Streamlit live dashboard
│       └── config_page.py       # Streamlit AI config page
├── config/
│   └── config.yml               # All trading parameters
├── requirements.txt
└── .env                         # Credentials (not committed)
```

## Prerequisites

- Python 3.8+
- Google Chrome installed
- Valid OON Boersespiel account
- An AI provider (one of):
  - Google AI Studio account (free, browser-based)
  - OpenAI API key
  - Anthropic (Claude) API key
  - Google Gemini API key
  - Ollama running locally

## Installation

```bash
git clone https://github.com/Gretoffel/oon-TradingBot.git
cd oon-TradingBot
pip install -r requirements.txt
python -m playwright install
```

Create a `.env` file in the project root:

```
BOERSEN_EMAIL=your_email@example.com
BOERSEN_PASSWORD=your_password
```

> [!NOTE]
> Never commit the `.env` file. It's already in `.gitignore`.

## Configuration

All trading parameters are in `config/config.yml`:

| Section | Examples |
|---|---|
| **Cycle Timing** | AI cycle interval (15min), quick check interval (60s) |
| **Risk Management** | Min trade volume, max invest per stock, portfolio diversity |
| **Strategy** | AI/tech weight, min final score, max candidates |
| **Profit/Loss** | Take profit (20%), stop loss (-2.5%) |
| **High Water Mark** | Trigger at 4% profit, sell on 1.5% drawdown |
| **Technical Indicators** | RSI period, EMA spans, volume ratio |
| **Browser** | Headless mode toggle |

## Usage

### Standard Mode

```bash
cd src
python main.py
```

If `web_config` is enabled in `config/ai_config.json`, a configuration page opens first to select the AI provider. Otherwise the bot starts directly.

**Do not close the browser windows manually** - the bot needs them for web automation.

### Bot Cycle

The bot runs two alternating cycles:

1. **Quick Check** (every 60s) - Fetches market data, checks stop-loss/trailing stop, executes emergency sells
2. **Full Strategy** (every 15min) - Runs AI defense check, technical scan, AI deep-dive analysis, and executes buy orders

### Web Dashboard

A Streamlit dashboard launches automatically at `http://localhost:8501`:

- Portfolio overview with performance and peak tracking
- Open orders
- Transaction history
- Live console output
- Pause/Resume controls

> [!TIP]
> Use ngrok or similar to access the dashboard remotely.

### Test Mode

Set `test_mode.enabled: true` in `config/config.yml` to run without executing real trades.

## Stopping the Bot

Press `Ctrl+C` to gracefully shut down, or use the Pause button in the dashboard.

## Logs

Transaction logs are stored in `logs/` with daily rotation:

```
logs/
  log_2026-02-10.txt
  log_2026-02-11.txt
```

Each entry contains: timestamp, action (BUY/SELL), stock name, ISIN, quantity, price, profit, and AI reasoning.

Session output is also logged to `logs/session_live.log`.

## View
![Alt](https://repobeats.axiom.co/api/embed/bd05277d35983dc94452e70861a04f46a3ec183f.svg "Repobeats analytics image")

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding standards, and pull request guidelines.

## License

This project is licensed under the [GNU General Public License v2.0](LICENSE).
