from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Customer, Address
from drf_spectacular.utils import extend_schema_field
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
import uuid
from rest_framework.validators import UniqueValidator


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    full_name = serializers.CharField(write_only=True)
    phone_number = serializers.CharField(
        write_only=True, required=False, allow_blank=True)
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all(), message="Email already exists")]
    )

    class Meta:
        model = User
        fields = ['id', 'username', 'email',
                  'password', 'full_name', 'phone_number']
        extra_kwargs = {
            'password': {
                'write_only': True,
                'style': {'input_type': 'password'}
            },
            'username': {
                'required': False,
            }
        }

    def create(self, validated_data):
        full_name = validated_data.pop('full_name')
        phone_number = validated_data.pop('phone_number', '')

        # Handle username: if not provided, generate from email
        if 'username' not in validated_data:
            email_prefix = validated_data['email'].split('@')[0]
            # Ensure uniqueness
            username = f"{email_prefix}_{uuid.uuid4().hex[:8]}"
            validated_data['username'] = username

        # Create User
        user = User.objects.create_user(**validated_data)

        # Update Customer profile (created via signal)
        # We need to refresh from db or access the related object
        if hasattr(user, 'customer'):
            customer = user.customer
            customer.name = full_name
            customer.phone_number = phone_number
            customer.save()

        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom serializer to allow login with email and password.
    """
    username_field = User.USERNAME_FIELD

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make username field optional so we can use email instead
        if self.username_field in self.fields:
            self.fields[self.username_field].required = False

        # Add email field
        self.fields['email'] = serializers.EmailField(required=False)

    def validate(self, attrs):
        # Map 'email' to 'username' if present, because the parent class expects 'username' (or USERNAME_FIELD)
        if 'email' in attrs and attrs.get('email'):
            attrs[self.username_field] = attrs['email']

        # If neither provided, raise error
        if not attrs.get(self.username_field) and not attrs.get('email'):
            raise serializers.ValidationError('Email or username is required.')

        return super().validate(attrs)

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token['email'] = user.email
        return token


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change endpoint.
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField()
    token = serializers.CharField()


class CustomerSerializer(serializers.ModelSerializer):
    """
    Read/Write customer details.
    """
    username = serializers.CharField(source='user.username', read_only=True)

    is_wholesaler = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            'id', 'user', 'username', 'name',
            'email', 'phone_number', 'customer_type',
            'is_wholesaler', 'created_at'
        ]
        read_only_fields = ['user', 'customer_type', 'created_at']

    @extend_schema_field(serializers.BooleanField())
    def get_is_wholesaler(self, obj):
        return obj.is_wholesaler


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
