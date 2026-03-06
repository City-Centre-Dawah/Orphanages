"""Tests for webhooks app."""

import hashlib
import hmac
import json
from unittest.mock import patch

from django.test import Client, TestCase, override_settings


class WhatsAppWebhookVerificationTest(TestCase):
    """Meta Cloud API GET verification handshake."""

    def setUp(self):
        self.client = Client()
        self.webhook_url = "/webhooks/whatsapp/"

    @override_settings(WHATSAPP_VERIFY_TOKEN="my-verify-token")
    def test_verification_success(self):
        """GET with correct verify_token echoes hub.challenge."""
        response = self.client.get(
            self.webhook_url,
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "my-verify-token",
                "hub.challenge": "challenge_string_123",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "challenge_string_123")

    @override_settings(WHATSAPP_VERIFY_TOKEN="my-verify-token")
    def test_verification_wrong_token(self):
        """GET with wrong verify_token returns 403."""
        response = self.client.get(
            self.webhook_url,
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong-token",
                "hub.challenge": "challenge_string_123",
            },
        )
        self.assertEqual(response.status_code, 403)


class WhatsAppWebhookMessageTest(TestCase):
    """Meta Cloud API POST message handling."""

    def setUp(self):
        self.client = Client()
        self.webhook_url = "/webhooks/whatsapp/"
        self.valid_payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "123456",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "441234567890",
                                    "phone_number_id": "PHONE_ID",
                                },
                                "messages": [
                                    {
                                        "id": "wamid.abc123",
                                        "from": "256700000000",
                                        "timestamp": "1234567890",
                                        "type": "text",
                                        "text": {"body": "Food 50000 rice"},
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }

    @override_settings(WHATSAPP_APP_SECRET="", DEBUG=True)
    @patch("webhooks.tasks.process_whatsapp_message")
    def test_webhook_queues_task_in_dev_mode(self, mock_task):
        """Without app secret (dev), webhook accepts and queues."""
        mock_task.delay.return_value = None
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(self.valid_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        mock_task.delay.assert_called_once()

    @override_settings(WHATSAPP_APP_SECRET="test-secret", DEBUG=False)
    @patch("webhooks.tasks.process_whatsapp_message")
    def test_webhook_validates_signature(self, mock_task):
        """With app secret, valid HMAC signature is accepted."""
        mock_task.delay.return_value = None
        body = json.dumps(self.valid_payload).encode()
        signature = "sha256=" + hmac.new(
            b"test-secret", body, hashlib.sha256
        ).hexdigest()
        response = self.client.post(
            self.webhook_url,
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256=signature,
        )
        self.assertEqual(response.status_code, 200)
        mock_task.delay.assert_called_once()

    @override_settings(WHATSAPP_APP_SECRET="test-secret", DEBUG=False)
    def test_webhook_rejects_bad_signature(self):
        """With app secret, invalid HMAC signature returns 403."""
        body = json.dumps(self.valid_payload).encode()
        response = self.client.post(
            self.webhook_url,
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE_256="sha256=invalid",
        )
        self.assertEqual(response.status_code, 403)

    @override_settings(WHATSAPP_APP_SECRET="test-secret", DEBUG=False)
    def test_webhook_rejects_missing_signature(self):
        """With app secret, missing signature returns 403."""
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(self.valid_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    @override_settings(WHATSAPP_APP_SECRET="", DEBUG=False)
    def test_webhook_rejects_unconfigured_production(self):
        """In production without app secret, returns 503."""
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(self.valid_payload),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 503)
