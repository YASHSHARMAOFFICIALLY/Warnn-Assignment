from django.core.management.base import BaseCommand

from alerts.models import Service, Team


class Command(BaseCommand):
    help = "Create 2 teams and 3 services"

    def handle(self, *args, **options):
        payments, _ = Team.objects.get_or_create(name="Payments", defaults={"oncall": "pay-oncall@example.com"})
        platform, _ = Team.objects.get_or_create(name="Platform", defaults={"oncall": "plat-oncall@example.com"})
        Service.objects.get_or_create(name="checkout-api", defaults={"team": payments})
        Service.objects.get_or_create(name="billing-worker", defaults={"team": payments})
        Service.objects.get_or_create(name="auth-service", defaults={"team": platform})
        self.stdout.write("seeded")
