from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Customer, Address, Division, District, SubDistrict
from drf_spectacular.utils import extend_schema_field
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
import uuid
from rest_framework.validators import UniqueValidator
from allauth.account.models import EmailAddress


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

    def validate_email(self, value):
        # We don't want to reveal if the user exists, so we just return the value.
        # The view will handle the logic.
        return value


class ResetPasswordSerializer(serializers.Serializer):
    uidb64 = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(
        min_length=8,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        try:
            uid = urlsafe_base64_decode(attrs['uidb64']).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({"uidb64": "Invalid UID"})

        if not default_token_generator.check_token(user, attrs['token']):
            raise serializers.ValidationError({"token": "Invalid or expired token"})

        attrs['user'] = user
        return attrs

from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator


class CustomerSerializer(serializers.ModelSerializer):
    """
    Read/Write customer details.
    """
    username = serializers.CharField(source='user.username', read_only=True)
    is_wholesaler = serializers.SerializerMethodField()
    is_email_verified = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            'id', 'user', 'username', 'name',
            'email', 'phone_number', 'customer_type',
            'avatar', 'social_avatar_url', 'is_wholesaler', 'is_email_verified', 'is_staff', 'created_at'
        ]
        read_only_fields = ['user', 'customer_type', 'created_at']

    @extend_schema_field(serializers.BooleanField())
    def get_is_wholesaler(self, obj):
        return obj.is_wholesaler

    @extend_schema_field(serializers.BooleanField())
    def get_is_email_verified(self, obj):
        return EmailAddress.objects.filter(user=obj.user, verified=True).exists()

    def to_representation(self, instance):
        """
        Dynamically handle name and avatar fallbacks for the frontend.
        """
        data = super().to_representation(instance)
        
        # 1. Handle Name Fallback
        if not instance.name or not instance.name.strip():
            user = instance.user
            full_name = f"{user.first_name} {user.last_name}".strip()
            data['name'] = full_name if full_name else user.username
            
        # 2. Handle Avatar Fallback
        # If no custom avatar uploaded, check social_avatar_url
        if not instance.avatar:
            if instance.social_avatar_url:
                data['avatar'] = instance.social_avatar_url
            else:
                data['avatar'] = None
        else:
            # If there is a local avatar, super().to_representation 
            # already provided the absolute URL via the default field.
            pass
            
        return data


class AddressSerializer(serializers.ModelSerializer):
    """
    Matches the UI screenshot exactly.
    """
    division = serializers.SlugRelatedField(slug_field='name', queryset=Division.objects.all())
    district = serializers.SlugRelatedField(slug_field='name', queryset=District.objects.all())
    sub_district = serializers.SlugRelatedField(slug_field='name', queryset=SubDistrict.objects.all())

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


# --- Location Serializers ---

class DivisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Division
        fields = ['id', 'name', 'bn_name', 'lat', 'long']

class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = ['id', 'division', 'name', 'bn_name', 'lat', 'long']

class SubDistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubDistrict
        fields = ['id', 'district', 'name', 'bn_name']


class ResendVerificationEmailSerializer(serializers.Serializer):
    """Admin can supply any email to resend the verification link to."""
    email = serializers.EmailField(
        required=True,
        help_text="Email address to resend the verification link to."
    )

