from django.core.management.base import BaseCommand
from django.db.models import F
from inventory.models import Stock
from notifications.emails import send_low_stock_alert
from notifications.utils import get_warehouse_managers


class Command(BaseCommand):
    help = 'Check stock levels and email alerts for low stock items'

    def handle(self, *args, **options):
        # Find all stock records below minimum
        low_stock = Stock.objects.filter(
            quantity__lte=F('item__minimum_stock'),
            item__minimum_stock__gt=0,
            item__is_active=True,
            warehouse__is_active=True,
        ).select_related(
            'item', 'item__unit', 'item__category', 'warehouse'
        ).order_by('item__name')

        count = low_stock.count()

        if count == 0:
            self.stdout.write(
                self.style.SUCCESS("All stock levels are healthy. No alerts sent.")
            )
            return

        self.stdout.write(
            f"Found {count} low stock items. Sending alerts..."
        )

        recipients = get_warehouse_managers()

        if not recipients:
            self.stdout.write(
                self.style.WARNING(
                    "No Warehouse Managers found to notify. "
                    "Check user permissions."
                )
            )
            return

        send_low_stock_alert(low_stock, recipients)

        for user in recipients:
            self.stdout.write(
                self.style.SUCCESS(f"  Alert sent to: {user.email}")
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. {count} low stock items reported to "
                f"{len(recipients)} recipient(s)."
            )
        )