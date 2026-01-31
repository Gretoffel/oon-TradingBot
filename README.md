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

```bash
git clone https://github.com/Gretoffel/oon-TradingBot.git
cd oon-TradingBot
```

## Install dependencies

```bash 
pip install playwright python-dotenv streamlit
python -m playwright install
```

## Configure environment variables

- Create a .env file in the project root:

```
BOERSEN_EMAIL=your_email@example.com
BOERSEN_PASSWORD=your_password
API_KEY=your_google_api_key
```

> Security Note: Never commit the .env file to version control. It's already included in .gitignore.

## Usage

### Standard Mode (with AI & Dashboard)

```bash
python main.py
```

The bot will automatically:
1. Start the **Web Dashboard** (usually at `http://localhost:8501`)
2. Log into your OÖN account in a browser window
3. Scrape current portfolio data
4. Send data to Google AI for analysis
5. Execute recommended trades
6. Sleep for the configured duration (default: 3 min)

**Do not close the opened browser windows manually**, as the bot needs them to interact with the sites.

### Web Dashboard
Note: It is recommended to use ngrok in order to remotely access the dashboard.

The included Streamlit dashboard provides a real-time interface to:
- Monitor the bot's current status (Active, Sleeping, Error)
- View the latest portfolio balance
- See the last log messages
- **Pause/Resume** the bot remotely
- Stop the bot safely

### Test Mode (without AI)
Edit config.py:

```python
TEST_MODE = True

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

| Variable | Default | Description |
|----------|---------|-------------|
| `SUCCESS_WAIT_SECONDS` | 300 (5 min) | Wait time between successful cycles |
| `ERROR_WAIT_SECONDS` | 10 | Wait time after errors before retry |
| `TEST_MODE` | `False` | Enable/disable test mode (uses `TEST_ORDERS` instead of AI) |
| `LOG_DIR` | `./logs` | Directory for transaction logs |

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