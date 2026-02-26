"""Send WhatsApp replies via Twilio."""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def send_whatsapp_reply(from_our_number: str, to_user_number: str, body: str) -> bool:
    """
    Send a WhatsApp message to the user (reply within 24h session).
    from_our_number: our Twilio WhatsApp number (To from webhook)
    to_user_number: user's number (From from webhook)
    Returns True on success.
    """
    if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
        logger.info("Twilio not configured, skipping WhatsApp reply")
        return False

    # Ensure whatsapp: prefix
    from_addr = (
        f"whatsapp:{from_our_number}"
        if not from_our_number.startswith("whatsapp:")
        else from_our_number
    )
    to_addr = (
        f"whatsapp:{to_user_number}"
        if not to_user_number.startswith("whatsapp:")
        else to_user_number
    )

    try:
        from twilio.rest import Client

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(from_=from_addr, to=to_addr, body=body)
        logger.info("WhatsApp reply sent to %s", to_user_number[:6])
        return True
    except Exception as e:
        logger.exception("Failed to send WhatsApp reply: %s", e)
        return False
