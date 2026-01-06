from django.db import migrations


def set_sku_to_product_id(apps, schema_editor):
    Product = apps.get_model('products', 'Product')
    for p in Product.objects.all():
        if not p.product_id:
            continue
        p.sku = p.product_id
        p.save(update_fields=['sku'])


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0004_product_price'),
    ]

    operations = [
        migrations.RunPython(set_sku_to_product_id, migrations.RunPython.noop),
    ]
