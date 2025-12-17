from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from django.contrib.auth.models import User
from accounts.models import Customer, Address
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
            wholesale_price=80.00,
            stock_quantity=10,
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
        url = '/api/carts/'
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Cart.objects.count(), 1)
        self.assertEqual(Cart.objects.first().user, self.user)
