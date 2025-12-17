from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Customer, Address


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']
        extra_kwargs = {
            'password': {
                'write_only': True,
                # This ensures the Web UI shows a password box (******) not plain text
                'style': {'input_type': 'password'}
            }
        }

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change endpoint.
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class CustomerSerializer(serializers.ModelSerializer):
    """
    Read/Write customer details.
    """
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Customer
        fields = [
            'id', 'user', 'username', 'name',
            'email', 'phone_number', 'customer_type',
            'is_wholesaler', 'created_at'
        ]
        read_only_fields = ['user', 'customer_type', 'created_at']


class AddressSerializer(serializers.ModelSerializer):
    """
    Matches the UI screenshot exactly.
    """
    class Meta:
        model = Address
        fields = [
            'id',
            'full_name', 'phone',           # Contact
            'address',                      # House/Road
            'division', 'district', 'sub_district',  # Location
            'address_type', 'is_default'    # Meta
        ]

    def create(self, validated_data):
        # Automatically assign the logged-in user's customer profile
        user = self.context['request'].user
        validated_data['customer'] = user.customer
        return super().create(validated_data)
