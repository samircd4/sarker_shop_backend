from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from accounts.models import Address
from products.models import Product, Category, Brand
from .models import Order, OrderStatus, PaymentInfo, Cart


class OrderAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create User & Customer
        self.user = User.objects.create_user(
            username='testuser', password='password', email='test@example.com')
        # Signal creates Customer automatically
        self.customer = self.user.customer
        self.customer.name = 'Test Customer'
        self.customer.save()

        self.client.force_authenticate(user=self.user)

        # Create Address
        self.address = Address.objects.create(
            customer=self.customer,
            full_name='Test Name',
            address='123 Test St',
            division='Dhaka',
            district='Dhaka City',
            sub_district='Dhanmondi',
            phone='1234567890'
        )

        # Create Product
        self.category = Category.objects.create(
            name='Electronics', slug='electronics')
        self.brand = Brand.objects.create(name='Sony', slug='sony')
        self.product = Product.objects.create(
            name='Headphones',
            slug='headphones',
            price=100.00,
            category=self.category,
            brand=self.brand
        )

    def test_create_order(self):
        url = '/api/orders/'
        data = {
            'items_input': [
                {'product_id': self.product.id, 'quantity': 2}
            ],
            'address_id': self.address.id
        }
        response = self.client.post(url, data, format='json')
        if response.status_code != status.HTTP_201_CREATED:
            print(response.data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Order.objects.first().total_amount, 200.00)

    def test_list_orders(self):
        # Create a dummy order
        status_pending = OrderStatus.objects.create(
            status_code='pending', display_name='Pending')
        payment = PaymentInfo.objects.create()
        Order.objects.create(
            customer=self.customer,
            order_status=status_pending,
            payment_info=payment,
            total_amount=50.00
        )

        url = '/api/orders/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Handle pagination
        if 'results' in response.data:
            self.assertEqual(len(response.data['results']), 1)
        else:
            self.assertEqual(len(response.data), 1)

    def test_create_order_with_variant_items_input(self):
        # Create a product with a variant
        product = Product.objects.create(
            name='Phone X',
            slug='phone-x',
            category=self.category,
            brand=self.brand
        )
        variant = product.variants.create(
            ram=8, storage=256, color='Blue',
            price=299.99, stock_quantity=10
        )
        url = '/api/orders/'
        data = {
            'items_input': [
                {'variant_id': variant.id, 'quantity': 3}
            ],
            'address_id': self.address.id
        }
        response = self.client.post(url, data, format='json')
        if response.status_code != status.HTTP_201_CREATED:
            print("Order creation error:", response.data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        items = response.data.get('items', [])
        self.assertTrue(len(items) >= 1)
        first = items[0]
        self.assertIsNotNone(first.get('variant'))
        self.assertEqual(first['quantity'], 3)
        self.assertEqual(first['ram'], 8)
        self.assertEqual(first['storage'], 256)
        self.assertEqual(first['color'], 'Blue')


class CartAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='cartuser', password='password', email='cart@example.com')
        # Customer auto-created by signal
        self.customer = self.user.customer
        self.client.force_authenticate(user=self.user)

        # Create dependencies for product
        self.category = Category.objects.create(name='Misc', slug='misc')
        self.brand = Brand.objects.create(name='Generic', slug='generic')

    def test_create_cart(self):
        url = '/api/cart/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Authenticated user gets or creates a cart associated with user
        self.assertEqual(Cart.objects.count(), 1)
        self.assertEqual(Cart.objects.first().user, self.user)


class CartAnonAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Create dependencies for product
        self.category = Category.objects.create(name='Misc', slug='misc')
        self.brand = Brand.objects.create(name='Generic', slug='generic')
        self.product = Product.objects.create(
            name='SimpleProd',
            slug='simpleprod',
            price=50.00,
            category=self.category,
            brand=self.brand
        )

    def test_anon_cart_add_product(self):
        # Initially list cart (should create a session-based cart)
        list_url = '/api/cart/'
        r1 = self.client.get(list_url)
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        self.assertEqual(Cart.objects.count(), 1)
        cart = Cart.objects.first()
        self.assertIsNone(cart.user)
        self.assertIsNotNone(cart.session_key)

        # Add product to cart
        create_url = '/api/cart/'
        payload = {'product_id': self.product.id, 'quantity': 2}
        r2 = self.client.post(create_url, payload, format='json')
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED)

        # Confirm item present
        r3 = self.client.get(list_url)
        self.assertEqual(r3.status_code, status.HTTP_200_OK)
        self.assertTrue(len(r3.data.get('items', [])) >= 1)

    def test_anon_order_from_cart_with_variant(self):
        # Create product with variant
        product = Product.objects.create(
            name='Phone',
            slug='phone',
            category=self.category,
            brand=self.brand
        )
        variant = product.variants.create(
            ram=8, storage=128, color='Black',
            price=199.99, stock_quantity=5
        )

        # Ensure cart exists
        list_url = '/api/cart/'
        self.client.get(list_url)

        # Add variant to cart
        add_url = '/api/cart/'
        payload = {'variant_id': variant.id, 'quantity': 2}
        r_add = self.client.post(add_url, payload, format='json')
        self.assertEqual(r_add.status_code, status.HTTP_201_CREATED)

        # Create order from cart (guest fields required)
        order_url = '/api/orders/'
        order_payload = {
            'email': 'guest@example.com',
            'full_name': 'Guest User',
            'phone': '0123456789',
            'shipping_address': '123 Street',
            'division': 'Dhaka',
            'district': 'Dhaka',
        }
        r_order = self.client.post(order_url, order_payload, format='json')
        if r_order.status_code != status.HTTP_201_CREATED:
            print("Order creation error:", r_order.data)
        self.assertEqual(r_order.status_code, status.HTTP_201_CREATED)
        # Check items include variant details
        data = r_order.data
        items = data.get('items', [])
        self.assertTrue(len(items) >= 1)
        first = items[0]
        self.assertIsNotNone(first.get('variant'))
        self.assertEqual(first['quantity'], 2)
        self.assertEqual(first['ram'], 8)
        self.assertEqual(first['storage'], 128)
        self.assertEqual(first['color'], 'Black')
