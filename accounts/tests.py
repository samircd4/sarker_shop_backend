from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status


class AuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('auth_register')
        self.login_url = reverse('token_obtain_pair')
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpassword123'
        }

    def test_registration(self):
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='testuser').exists())

    def test_login(self):
        self.client.post(self.register_url, self.user_data)
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'testpassword123'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_profile_creation(self):
        # Customer profile should be created automatically via signal
        self.client.post(self.register_url, self.user_data)
        user = User.objects.get(username='testuser')
        self.assertTrue(hasattr(user, 'customer'))
        self.assertEqual(user.customer.email, 'test@example.com')

    def test_profile_view(self):
        # Register and Login
        self.client.post(self.register_url, self.user_data)
        login_res = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'testpassword123'
        })
        access_token = login_res.data['access']

        # Access Profile
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        url = reverse('customer-list') + 'me/'
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'test@example.com')

    def test_change_password(self):
        # Register and Login
        self.client.post(self.register_url, self.user_data)
        login_res = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'testpassword123'
        })
        access_token = login_res.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # Change Password
        change_password_url = reverse('change_password')
        response = self.client.put(change_password_url, {
            'old_password': 'testpassword123',
            'new_password': 'newpassword123'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify old password doesn't work
        login_res_old = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'testpassword123'
        })
        self.assertEqual(login_res_old.status_code,
                         status.HTTP_401_UNAUTHORIZED)

        # Verify new password works
        login_res_new = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'newpassword123'
        })
        self.assertEqual(login_res_new.status_code, status.HTTP_200_OK)
