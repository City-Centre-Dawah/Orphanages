"""Send Telegram replies via Bot API."""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"


def send_telegram_reply(chat_id: int, body: str, parse_mode: str = "") -> bool:
    """
    Send a text message to a Telegram chat via Bot API.

    Args:
        parse_mode: "MarkdownV2", "HTML", or "" for plain text.
    Returns True on success.
    """
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    if not token:
        logger.info("Telegram bot not configured, skipping reply to chat %s", chat_id)
        return False

    url = f"{TELEGRAM_API_BASE.format(token=token)}/sendMessage"
    payload = {"chat_id": chat_id, "text": body}
    if parse_mode:
        payload["parse_mode"] = parse_mode

    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200 and resp.json().get("ok"):
            logger.info("Telegram reply sent to chat %s", chat_id)
            return True
        logger.warning("Telegram sendMessage failed: %s", resp.text[:200])
        return False
    except Exception as e:
        logger.exception("Failed to send Telegram reply: %s", e)
        return False


def get_telegram_file_url(file_id: str) -> str:
    """
    Resolve a Telegram file_id to a downloadable URL.
    Returns empty string on failure.
    """
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    if not token:
        return ""

    url = f"{TELEGRAM_API_BASE.format(token=token)}/getFile"
    try:
        resp = requests.post(url, json={"file_id": file_id}, timeout=10)
        if resp.status_code == 200 and resp.json().get("ok"):
            file_path = resp.json()["result"]["file_path"]
            return f"https://api.telegram.org/file/bot{token}/{file_path}"
    except Exception as e:
        logger.warning("Failed to resolve Telegram file: %s", e)

    return ""
