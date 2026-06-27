from django.core.management.base import BaseCommand
from assets.models import AssetCategory


class Command(BaseCommand):
    help = 'Seed default asset categories'

    def handle(self, *args, **kwargs):
        categories = [
            ("Power Tools", "Electric and battery-powered tools"),
            ("Hand Tools", "Manual tools and implements"),
            ("Heavy Equipment", "Excavators, loaders, compactors"),
            ("Vehicles", "Trucks, pickups, vans"),
            ("Safety Equipment", "PPE and safety gear"),
            ("Measuring Instruments", "Survey and measurement tools"),
            ("IT Equipment", "Computers, tablets, phones"),
            ("Generators & Power", "Generators and power equipment"),
        ]
        for name, description in categories:
            AssetCategory.objects.get_or_create(
                name=name,
                defaults={'description': description}
            )
            self.stdout.write(f"  Ready: {name}")

        self.stdout.write(self.style.SUCCESS("Asset categories seeded."))