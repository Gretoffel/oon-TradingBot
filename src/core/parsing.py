import re
import json


def clean_amount(text):
    """Parse a European-formatted amount string (e.g. '1.200,50') into a float."""
    if not text:
        return 0.0

    cleaned = re.sub(r'[^\d,.-]', '', str(text))

    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace('.', '')

    cleaned = cleaned.replace(',', '.')

    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def calculate_fee(amount_eur):
    """
    Calculate transaction fees per OON Boersespiel rules.

    Fee structure:
    - 0.25% of transaction value
    - Minimum base fee: 17 EUR
    - Flat surcharge: 3 EUR per order
    """
    if amount_eur <= 0:
        return 0.0

    base_fee = max(17.0, amount_eur * 0.0025)
    return base_fee + 3.0


def extract_json_list(text):
    """Extract a JSON list from a text block (e.g. an AI response)."""
    if not text:
        return None

    try:
        text = text.replace('```json', '').replace('```', '')
        text = re.sub(r'\[\d+\]', '', text)

        start = text.find('[')
        end = text.rfind(']')

        if start == -1 or end == -1:
            return None

        return json.loads(text[start : end + 1])
    except (json.JSONDecodeError, ValueError):
        return None
