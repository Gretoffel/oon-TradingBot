# OÖN Trading Bot
An automated trading bot for the OÖN Börsenspiel (OÖN Stock Market Game) using AI-powered decision making and web automation.
Overview
This bot automates participation in the OÖN stock trading simulation by:

Scraping portfolio data from the web interface
Analyzing market conditions using Google AI Studio with search capabilities
Executing buy/sell orders automatically
Tracking performance and maintaining transaction logs

⚠️ Important: This is a research/educational project. See Known Issues & Limitations before deployment.
Architecture


- ✅ Automated Trading: Executes buy/sell orders based on AI analysis
- ✅ AI-Powered Decisions: Uses Google AI Studio with web search for market research
- ✅ Portfolio Tracking: Monitors cash, holdings, and open orders
- ✅ Performance Metrics: Tracks gains/losses since purchase
- ✅ Transaction Logging: Maintains daily log files of all actions
- ✅ Test Mode: Dry-run capability without AI calls
- ✅ Auto-Recovery: Supervisor pattern with automatic restart on errors

## Prerequisites

- Python 3.8+
- Google AI Studio account (free tier available)
- Valid OÖN Börsenspiel account

## Installation

1. Clone the repository

```bashgit clone https://github.com/Gretoffel/oon-TradingBot.git
cd oon-TradingBot
```

## Install dependencies

```bash 
pip install playwright python-dotenv
python -m playwright install
```

## Configure environment variables

- Create a .env file in the project root:

```
envBOERSEN_EMAIL=your_email@example.com
BOERSEN_PASSWORD=your_password
API_KEY=your_google_api_key
```

> Security Note: Never commit the .env file to version control. It's already included in .gitignore.

## Usage
Standard Mode (with AI)
bashpython main.py
The bot will:

- Log into your OÖN account
- Scrape current portfolio data
- Send data to Google AI for analysis
- Execute recommended trades
- Wait 3 minutes and repeat

### Test Mode (without AI)
Edit config.py:

```py
pythonTEST_MODE = True
TEST_ORDERS = [
    {
        "aktion": "BUY",
        "name": "Apple Inc.",
        "isin": "US0378331005",
        "betrag_eur": 1000,
        "grund": "Testing buy order execution"
    }
]
```

Then run python main.py to test order execution without AI calls.

## Stopping the Bot
Press CTRL+C to gracefully shut down.

## Configuration
Key settings in config.py:

```py
VariableDefaultDescriptionSUCCESS_WAIT_SECONDS180 (3 min)Wait time between successful cyclesERROR_WAIT_SECONDS10Wait time after errors before retryTEST_MODEFalseEnable/disable test modeLOG_DIR./logsDirectory for transaction logs
```

## Logs
Transaction logs are stored in ./logs/ with daily rotation:

logs/
  log_2026-01-29.txt
  log_2026-01-30.txt

Each entry contains:

- Timestamp
- Action (BUY/SELL)
- Stock name and ISIN
- Quantity and estimated price
- AI reasoning

## License
This Project is under the `GNU General Public License version 2.0`, see LICENSE File for more information