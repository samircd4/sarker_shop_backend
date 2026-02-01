import os
import json
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_api.settings')
django.setup()

from accounts.models import District, SubDistrict

def populate_subdistricts():
    print("Loading Sub-Districts from JSON...")
    
    file_path = os.path.join('accounts', 'upozillas.json')
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    upazilas = data.get('upazilas', [])
    print(f"Found {len(upazilas)} upazilas to process.")

    print("Wiping existing Sub-Districts...")
    SubDistrict.objects.all().delete()
    
    count = 0
    errors = 0
    
    for item in upazilas:
        try:
            district_id = item['district_id']
            # Lookup district
            district = District.objects.get(id=district_id)
            
            SubDistrict.objects.create(
                id=item['id'],
                district=district,
                name=item['name'],
                bn_name=item.get('bn_name', '')
            )
            count += 1
        except District.DoesNotExist:
            print(f"Error: District ID {item['district_id']} not found for Upazila {item['name']}")
            errors += 1
        except Exception as e:
            print(f"Error creating Upazila {item['name']}: {e}")
            errors += 1
            
    print(f"Finished. Created: {count}, Errors: {errors}")

if __name__ == '__main__':
    populate_subdistricts()
