import asyncio
import json
import os
from datetime import datetime
import config
from utils import extract_json_list, get_todays_log_content
from browser_utils import check_soft_crash

async def _send_prompt_to_ai(page, context, prompt):
    """Internal helper to manage AI Studio interaction."""
    max_ai_retries = 3
    ai_success = False
    response_text = ""

    for attempt in range(max_ai_retries):
        try:
            if page.is_closed():
                page = await context.new_page()

            if page.url != config.AI_STUDIO_URL:
                await page.goto(config.AI_STUDIO_URL)
                await asyncio.sleep(4)
            
            if await check_soft_crash(page):
                continue

            # Check for Login
            if "accounts.google.com" in page.url or "signin" in page.url:
                print("\n🔑 Google Login required. Waiting...")
                await page.wait_for_selector("div[contenteditable='true'], textarea", state="visible", timeout=3599000)
            else:
                await page.wait_for_selector("div[contenteditable='true'], textarea", state="visible", timeout=8000)
            
            await page.fill("div[contenteditable='true'], textarea", prompt)
            
            run_btn = page.locator(".run-button-label", has_text="Run")
            if await run_btn.count() > 0: await run_btn.click()
            else: await page.keyboard.press("Control+Enter")

            last_text_len = 0 
            for poll_tick in range(15): 
                await asyncio.sleep(4) 
                
                if await check_soft_crash(page): break 

                error_locator = page.locator(".model-error")
                if await error_locator.count() > 0 and await error_locator.last.is_visible():
                    print("\n⚠️ Google AI Error detected. Attempting Rerun...")
                    try:
                        await error_locator.last.hover(force=True)
                        rerun_btns = page.locator("button[aria-label='Rerun this turn']")
                        if await rerun_btns.count() > 0:
                            await rerun_btns.last.click()
                            continue
                        else:
                            await page.reload()
                            break 
                    except: 
                        break 

                ans_locator = page.locator('div[data-turn-role="Model"]').last
                if await ans_locator.count() > 0:
                    current_text = await ans_locator.inner_text()
                    if len(current_text) >= 2 and "]" in current_text:
                        if len(current_text) == last_text_len:
                            response_text = current_text
                            
                            # --- NEW: VERBOSE LOGGING ---
                            print("\n" + "─"*50)
                            print("📝 RAW AI RESPONSE RECEIVED:")
                            print("─"*50)
                            print(response_text)
                            print("─"*50 + "\n")
                            # ---------------------------
                            
                            ai_success = True
                            break 
                        else: last_text_len = len(current_text)
                    else: last_text_len = len(current_text)
            
            if ai_success: break 

        except Exception as e:
            print(f"❌ AI Error: {e}")
            if any(x in str(e).lower() for x in ["crashed", "closed", "target"]):
                try: await page.close()
                except: pass
                page = await context.new_page()
            await asyncio.sleep(5)
            
    return response_text if ai_success else None

async def check_portfolio_safety(page, context, stocks):
    """Phase 1: Defense - Identify critical red flags for owned stocks."""
    if not stocks: return {}
    
    print("\n🛡️ AI DEFENSE: Checking portfolio for critical news...")
    
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
    
    response = await _send_prompt_to_ai(page, context, prompt)
    if response:
        decisions = extract_json_list(response)
        return decisions if decisions else []
    return []

async def analyze_candidates_deep_dive(page, context, candidates):
    """Phase 3: Synthesis - Detailed analysis for top 10 technical candidates."""
    if not candidates: return []
    
    print(f"\n🔍 AI DEEP-DIVE: Analyzing {len(candidates)} candidates...")
    
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
    
    response = await _send_prompt_to_ai(page, context, prompt)
    if response:
        matrix = extract_json_list(response)
        return matrix if matrix else []
    return []
