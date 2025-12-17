from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from .models import Category, Brand, Product, ProductVariant
from accounts.models import Customer
# Try importing Order/OrderItem, if fails, skip bestseller test
try:
    from orders.models import Order, OrderItem, OrderStatus, PaymentInfo, Cart
    ORDERS_APP_AVAILABLE = True
except ImportError:
    ORDERS_APP_AVAILABLE = False


class CatalogTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_superuser(
            'admin', 'admin@example.com', 'password')
        self.client.force_authenticate(user=self.user)

        # Setup basic data
        self.category = Category.objects.create(
            name='Electronics', slug='electronics')
        self.brand = Brand.objects.create(name='TechBrand', slug='techbrand')
        self.product = Product.objects.create(
            name='Smartphone',
            category=self.category,
            brand=self.brand,
            price=100.00,
            wholesale_price=80.00,
            sku='PHONE-001'
        )

    def test_category_hierarchy(self):
        # Create child category
        child_cat = Category.objects.create(
            name='Phones', parent=self.category)

        # Check API
        response = self.client.get(f'/api/categories/{self.category.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check children are serialized
        self.assertTrue(
            any(c['id'] == child_cat.id for c in response.data['children']))

        # Check breadcrumbs on child
        response = self.client.get(f'/api/categories/{child_cat.id}/')
        breadcrumbs = response.data['breadcrumbs']
        self.assertEqual(len(breadcrumbs), 2)
        self.assertEqual(breadcrumbs[0]['slug'], 'electronics')
        self.assertEqual(breadcrumbs[1]['slug'], 'phones')

    def test_product_variants(self):
        # Create variant via API (or just check model, but API test is better)
        # Using API to update product with variants
        url = f'/api/products/{self.product.id}/'
        # ... skipped update test ...

        create_url = '/api/products/'
        new_product_data = {
            'name': 'New Phone',
            'category_id': self.category.id,
            'brand_id': self.brand.id,
            'price': 200.00,
            'wholesale_price': 150.00,
            'variants_input': [
                {'name': 'Variant A', 'sku': 'VAR-A', 'stock_quantity': 10}
            ]
        }
        response = self.client.post(
            create_url, new_product_data, format='json')
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Create Error: {response.data}")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        product_id = response.data['id']

        # Verify variants created
        product = Product.objects.get(id=product_id)
        self.assertEqual(product.variants.count(), 1)
        self.assertEqual(product.variants.first().name, 'Variant A')

    def test_product_actions(self):
        # Featured
        self.product.is_featured = True
        self.product.save()

        response = self.client.get('/api/products/featured/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.product.id)

        # Related
        other_product = Product.objects.create(
            name='Case', category=self.category, brand=self.brand, price=10, wholesale_price=5
        )
        self.product.related_products.add(other_product)

        response = self.client.get(f'/api/products/{self.product.id}/related/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], other_product.id)

    def test_search_and_filter(self):
        # Test Search
        response = self.client.get('/api/products/?search=Smartphone')
        self.assertEqual(len(response.data['results']), 1)

        response = self.client.get('/api/products/?search=Banana')
        self.assertEqual(len(response.data['results']), 0)

        # Test Filter
        response = self.client.get(f'/api/products/?brand={self.brand.id}')
        self.assertEqual(len(response.data['results']), 1)

    def test_bestsellers_dynamic(self):
        if not ORDERS_APP_AVAILABLE:
            return

        # Create an order for the product
        customer = self.user.customer  # Use existing customer
        order_status, _ = OrderStatus.objects.get_or_create(
            status_code='completed')
        payment_info = PaymentInfo.objects.create()

        order = Order.objects.create(
            customer=customer,
            order_status=order_status,
            payment_info=payment_info,
            total_amount=100
        )
        OrderItem.objects.create(
            order=order, product=self.product, price=100, quantity=5)

        # Another product with no sales
        Product.objects.create(name='Unpopular', category=self.category,
                               brand=self.brand, price=10, wholesale_price=5)

        response = self.client.get('/api/products/bestsellers/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertTrue(len(results) >= 1)
        self.assertEqual(results[0]['id'], self.product.id)
