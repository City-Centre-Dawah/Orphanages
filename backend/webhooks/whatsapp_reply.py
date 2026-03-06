"""Send WhatsApp replies and fetch media via Meta Cloud API (Graph API)."""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

GRAPH_API_URL = "https://graph.facebook.com/v21.0"


def send_whatsapp_reply(to_number: str, body: str) -> bool:
    """
    Send a WhatsApp text reply via Meta Cloud API.

    Args:
        to_number: Recipient phone in E.164 format (with or without +).
        body: Message text.

    Returns True on success.
    """
    if not settings.WHATSAPP_ACCESS_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        logger.info("WhatsApp Cloud API not configured, skipping reply")
        return False

    url = f"{GRAPH_API_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to_number.lstrip("+"),
        "type": "text",
        "text": {"body": body},
    }

    try:
        resp = requests.post(url, json=data, headers=headers, timeout=10)
        resp.raise_for_status()
        logger.info("WhatsApp reply sent to %s", to_number[:6])
        return True
    except Exception as e:
        logger.exception("Failed to send WhatsApp reply: %s", e)
        return False


def get_whatsapp_media_url(media_id: str) -> str:
    """
    Fetch the download URL for a WhatsApp media ID.

    Meta returns a temporary URL that requires the Bearer token to download.

    Args:
        media_id: The media ID from the webhook payload.

    Returns the download URL, or empty string on failure.
    """
    if not settings.WHATSAPP_ACCESS_TOKEN:
        logger.warning("WhatsApp access token not configured, cannot fetch media")
        return ""

    url = f"{GRAPH_API_URL}/{media_id}"
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json().get("url", "")
    except Exception as e:
        logger.warning("Failed to fetch WhatsApp media URL for %s: %s", media_id, e)
        return ""
