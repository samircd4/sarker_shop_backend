import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_api.settings')
django.setup()

from accounts.models import Division

divisions = [
    "Barishal",
    "Chattogram",
    "Dhaka",
    "Khulna",
    "Mymensingh",
    "Rajshahi",
    "Rangpur",
    "Sylhet"
]

print("Starting to seed divisions...")
for div_name in divisions:
    obj, created = Division.objects.get_or_create(name=div_name)
    if created:
        print(f"Created: {div_name}")
    else:
        print(f"Already exists: {div_name}")

print("Finished seeding divisions.")
