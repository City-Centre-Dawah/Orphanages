"""SMS sending via Africa's Talking."""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def send_sms(to_number: str, message: str) -> bool:
    """
    Send SMS via Africa's Talking.
    Returns True on success, False otherwise.
    """
    if not getattr(settings, "AFRICAS_TALKING_API_KEY", None):
        logger.info("Africa's Talking not configured, skipping SMS to %s", to_number[:6])
        return False

    try:
        import africastalking

        africastalking.initialize(
            settings.AFRICAS_TALKING_USERNAME,
            settings.AFRICAS_TALKING_API_KEY,
        )
        sms = africastalking.SMS
        response = sms.send(message, [to_number])
        recipients = response.get("SMSMessageData", {}).get("Recipients", [])
        if recipients and recipients[0].get("status") == "Success":
            logger.info("SMS sent to %s", to_number[:6])
            return True
        logger.warning("Africa's Talking response: %s", response)
        return False
    except Exception as e:
        logger.exception("Failed to send SMS: %s", e)
        return False
