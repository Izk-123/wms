from django.core.management.base import BaseCommand
from inventory.models import Unit, Warehouse, Category


class Command(BaseCommand):
    help = 'Seed default units, categories, and warehouses'

    def handle(self, *args, **kwargs):

        # Units
        units = [
            ("Kilogram", "kg"), ("Ton", "t"), ("Bag", "bag"),
            ("Piece", "pcs"), ("Liter", "L"), ("Meter", "m"),
            ("Square Meter", "m²"), ("Cubic Meter", "m³"),
            ("Roll", "roll"), ("Box", "box"), ("Drum", "drum"),
        ]
        for name, symbol in units:
            Unit.objects.get_or_create(name=name, defaults={'symbol': symbol})
        self.stdout.write(self.style.SUCCESS("Units ready."))

        # Categories
        categories = [
            "Cement & Concrete", "Steel & Metal", "Timber & Wood",
            "Aggregates", "Plumbing", "Electrical",
            "Paint & Finishes", "Tools", "Safety Equipment",
            "Spare Parts", "Consumables", "Finished Goods",
        ]
        for name in categories:
            Category.objects.get_or_create(name=name)
        self.stdout.write(self.style.SUCCESS("Categories ready."))

        # Warehouses
        warehouses = [
            ("Main Warehouse", "Head Office - Blantyre"),
            ("Site Store A", "Construction Site A"),
            ("Site Store B", "Construction Site B"),
        ]
        for name, location in warehouses:
            Warehouse.objects.get_or_create(
                name=name,
                defaults={'location': location}
            )
        self.stdout.write(self.style.SUCCESS("Warehouses ready."))