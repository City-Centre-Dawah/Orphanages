"""Management command to manually trigger exchange rate update."""

from django.core.management.base import BaseCommand

from expenses.tasks import update_exchange_rates


class Command(BaseCommand):
    help = "Fetch latest exchange rates from exchangerate-api.com and update the database."

    def handle(self, *args, **options):
        self.stdout.write("Fetching exchange rates...")
        result = update_exchange_rates()
        self.stdout.write(self.style.SUCCESS(f"Result: {result}"))
