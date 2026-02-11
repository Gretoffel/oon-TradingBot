import json
from datetime import datetime
from utils import extract_json_list, get_todays_log_content


async def check_portfolio_safety(provider, stocks):
    """Phase 1: Defense - Identify critical red flags for owned stocks."""
    if not stocks: return {}

    print("\n  AI DEFENSE: Checking portfolio for critical news...")

    stock_list = [f"{s['name']} (ISIN: {s.get('isin', 'N/A')})" for s in stocks]

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prompt = f"""
    CURRENT DATE/TIME: {current_time} CET.
    TASK: Portfolio Defense Check.

    Act as a professional risk manager. Research the following stocks for CRITICAL news from the last 24-48 hours that would justify an IMMEDIATE EMERGENCY SALE.

    STOCKS TO CHECK:
    {json.dumps(stock_list)}

    INSTRUCTIONS:
    1. Be objective and factual.
    2. Only suggest 'EMERGENCY_SELL' if there is a 'Red Flag' news event.
    3. If there is no such event, suggest 'HOLD'.
    4. Provide a very brief reason (max 10 words) for SELL decisions.

    OUTPUT FORMAT (Strict JSON):
    [
        {{"isin": "ISIN", "action": "HOLD"}},
        {{"isin": "ISIN", "action": "EMERGENCY_SELL", "reason": "Reason..."}}
    ]
    """

    response = await provider.send_prompt(prompt)
    if response:
        decisions = extract_json_list(response)
        return decisions if decisions else []
    return []

async def analyze_candidates_deep_dive(provider, candidates):
    """Phase 3: Synthesis - Detailed analysis for top candidates."""
    if not candidates: return []

    print(f"\n  AI DEEP-DIVE: Analyzing {len(candidates)} candidates...")

    candidate_info = [{
        "isin": c['isin'],
        "name": c['ticker'],
        "price": c['price']
    } for c in candidates]

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prompt = f"""
    CURRENT DATE/TIME: {current_time} CET.
    TASK: Stock Candidate Analysis Matrix.

    Act as a financial data analyst. For each stock listed below, find the following SPECIFIC data points:
    1. Next Earnings Date (estimate if not exact).
    2. Analyst Consensus Rating (1.0 to 5.0, where 1 is Strong Sell and 5 is Strong Buy).
    3. General News Sentiment (1.0 to 5.0, where 1 is Very Bearish and 5 is Very Bullish).

    CANDIDATES:
    {json.dumps(candidate_info)}

    INSTRUCTIONS:
    - Return DATA ONLY. Do not make recommendations.
    - Be as objective as possible.
    - Use '0' if a value cannot be found.
    - Output MUST be a JSON list of objects.

    OUTPUT FORMAT (Strict JSON):
    [
        {{
            "isin": "ISIN",
            "name": "Ticker",
            "earnings_date": "YYYY-MM-DD",
            "analyst_rating": 4.2,
            "news_sentiment": 3.5,
            "brief_summary": "Brief news context..."
        }}
    ]
    """

    response = await provider.send_prompt(prompt)
    if response:
        matrix = extract_json_list(response)
        return matrix if matrix else []
    return []
