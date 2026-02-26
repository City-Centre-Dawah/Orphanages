"""Tests for webhooks app."""

from unittest.mock import patch

from django.test import Client, TestCase, override_settings


class WhatsAppWebhookTest(TestCase):
    """WhatsApp webhook validates and queues correctly."""

    def setUp(self):
        self.client = Client()
        self.webhook_url = "/webhooks/whatsapp/"
        self.valid_post = {
            "MessageSid": "SM123",
            "From": "whatsapp:+256700000000",
            "To": "whatsapp:+441234567890",
            "Body": "Food 50000 rice",
            "NumMedia": "0",
        }

    @override_settings(TWILIO_AUTH_TOKEN="")
    @patch("webhooks.tasks.process_whatsapp_message")
    def test_webhook_queues_task_when_no_auth_token(self, mock_task):
        """Without auth token (dev), webhook accepts and queues."""
        mock_task.delay.return_value = None
        response = self.client.post(
            self.webhook_url,
            data=self.valid_post,
            content_type="application/x-www-form-urlencoded",
        )
        self.assertEqual(response.status_code, 200)
        mock_task.delay.assert_called_once()

    @override_settings(TWILIO_AUTH_TOKEN="test-token")
    def test_webhook_rejects_get(self):
        """Webhook only accepts POST."""
        response = self.client.get(self.webhook_url)
        self.assertEqual(response.status_code, 405)
