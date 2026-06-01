"""Express tracking bridge module.

This module should handle all express/logistics tracking logic,
but is currently not integrated into the main message flow.
The weixin.py platform handler still has express logic hardcoded.
"""
import re
import logging

logger = logging.getLogger(__name__)

TRACKING_NUMBER_PATTERN = re.compile(r'\b\d{12,15}\b')
EXPRESS_KEYWORDS = ['查', '快递', '物流', 'track', 'express', 'package']


def is_express_query(message: str) -> bool:
    """Check if a message is an express tracking query."""
    has_number = bool(TRACKING_NUMBER_PATTERN.search(message))
    has_keyword = any(kw in message for kw in EXPRESS_KEYWORDS)
    return has_number and has_keyword


def extract_tracking_number(message: str) -> str:
    """Extract tracking number from message."""
    match = TRACKING_NUMBER_PATTERN.search(message)
    return match.group() if match else ""


async def handle_express_message(user_id: str, message: str) -> str:
    """Handle an express tracking query end-to-end."""
    number = extract_tracking_number(message)
    if not number:
        return "No valid tracking number found in your message"

    # TODO: Actually call the express API
    logger.info(f"Express bridge handling tracking: {number}")
    return f"Tracking {number}: [Bridge not connected to API yet]"
