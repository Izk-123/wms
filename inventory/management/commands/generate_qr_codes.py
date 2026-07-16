from django.core.management.base import BaseCommand
from inventory.models import Item
from inventory.qr_service import generate_qr_and_barcode


class Command(BaseCommand):
    help = 'Generate QR codes and barcodes for all inventory items'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regenerate even if codes already exist',
        )

    def handle(self, *args, **options):
        force = options['force']
        items = Item.objects.filter(is_active=True)
        total = items.count()

        self.stdout.write(f"Processing {total} items...")

        success = 0
        failed = 0

        for item in items:
            # Skip if already has codes and not forcing
            if not force and item.qr_code and item.barcode_image:
                self.stdout.write(f"  Skipped (exists): {item.sku}")
                continue

            try:
                generate_qr_and_barcode(item)
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ {item.sku} — {item.name}")
                )
                success += 1
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  ✗ {item.sku} — {e}")
                )
                failed += 1

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"Done. {success} generated, {failed} failed.")
        )