import asyncio
from ai_providers.base_provider import AIProvider

AI_STUDIO_URL = "https://aistudio.google.com/app/prompts/new_chat"


class GoogleStudioProvider(AIProvider):
    """Google AI Studio via browser automation (Playwright)."""

    name = "google_studio"

    def __init__(self, context):
        self.context = context
        self.page = None

    async def _ensure_page(self):
        if self.page is None or self.page.is_closed():
            self.page = await self.context.new_page()
        return self.page

    async def send_prompt(self, prompt: str):
        from browser_utils import check_soft_crash

        max_retries = 3
        response_text = ""

        for attempt in range(max_retries):
            try:
                page = await self._ensure_page()

                if page.url != AI_STUDIO_URL:
                    await page.goto(AI_STUDIO_URL)
                    await asyncio.sleep(4)

                if await check_soft_crash(page):
                    continue

                # Check for Google Login
                if "accounts.google.com" in page.url or "signin" in page.url:
                    print("\n  Google Login required. Waiting...")
                    await page.wait_for_selector(
                        "div[contenteditable='true'], textarea",
                        state="visible",
                        timeout=3599000,
                    )
                else:
                    await page.wait_for_selector(
                        "div[contenteditable='true'], textarea",
                        state="visible",
                        timeout=8000,
                    )

                await page.fill("div[contenteditable='true'], textarea", prompt)

                run_btn = page.locator(".run-button-label", has_text="Run")
                if await run_btn.count() > 0:
                    await run_btn.click()
                else:
                    await page.keyboard.press("Control+Enter")

                last_text_len = 0
                ai_success = False
                for poll_tick in range(15):
                    await asyncio.sleep(4)

                    if await check_soft_crash(page):
                        break

                    error_locator = page.locator(
                        ".model-error, mat-error, .error-container"
                    )
                    if (
                        await error_locator.count() > 0
                        and await error_locator.last.is_visible()
                    ):
                        print("\n  Google AI Error detected. Attempting Rerun...")
                        try:
                            targets = [
                                page.locator('div[data-turn-role="Model"]').last,
                                error_locator.last,
                                page.locator("ms-model-turn").last,
                            ]
                            for target in targets:
                                if await target.count() > 0:
                                    box = await target.bounding_box()
                                    if box:
                                        await page.mouse.move(
                                            box["x"] + box["width"] / 2,
                                            box["y"] + box["height"] - 10,
                                        )
                                        await asyncio.sleep(0.5)
                                        await page.mouse.move(
                                            box["x"] + box["width"] / 2 + 5,
                                            box["y"] + box["height"] - 15,
                                        )
                                        await asyncio.sleep(0.5)
                                    else:
                                        await target.hover(force=True)
                                        await asyncio.sleep(0.5)

                            await asyncio.sleep(1)
                            rerun_btns = page.locator(
                                "button[aria-label='Rerun this turn'], button:has-text('Rerun')"
                            )
                            if await rerun_btns.count() > 0:
                                print("   Clicking Rerun button...")
                                await rerun_btns.last.click()
                                await asyncio.sleep(2)
                                continue
                            else:
                                print(
                                    "   Rerun button not found. Reloading page as fallback..."
                                )
                                await page.reload()
                                await asyncio.sleep(4)
                                break
                        except Exception as re_err:
                            print(f"   Rerun failed: {re_err}")
                            break

                    ans_locator = page.locator(
                        'div[data-turn-role="Model"]'
                    ).last
                    if await ans_locator.count() > 0:
                        current_text = await ans_locator.inner_text()
                        if len(current_text) >= 2 and "]" in current_text:
                            if len(current_text) == last_text_len:
                                response_text = current_text
                                print("\n" + "-" * 50)
                                print("RAW AI RESPONSE RECEIVED:")
                                print("-" * 50)
                                print(response_text)
                                print("-" * 50 + "\n")
                                ai_success = True
                                break
                            else:
                                last_text_len = len(current_text)
                        else:
                            last_text_len = len(current_text)

                if ai_success:
                    return response_text

            except Exception as e:
                print(f"AI Error (Google Studio): {e}")
                if any(
                    x in str(e).lower() for x in ["crashed", "closed", "target"]
                ):
                    try:
                        await self.page.close()
                    except:
                        pass
                    self.page = None
                await asyncio.sleep(5)

        return None

    async def cleanup(self):
        if self.page and not self.page.is_closed():
            try:
                await self.page.close()
            except:
                pass
