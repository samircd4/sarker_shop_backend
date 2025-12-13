from django.contrib.auth.models import User
from rest_framework import generics, permissions, status
from rest_framework.serializers import ModelSerializer
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# --- Serializers ---

class RegisterSerializer(ModelSerializer):
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

# --- Views ---

class RegisterView(generics.CreateAPIView):
    """
    Handles user registration.
    Added 'get' method to render the form in the Browser.
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        # This returns an empty response, which DRF renders as the HTML Form
        return Response()


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Login View: Extends SimpleJWT to allow GET requests (HTML Form).
    """
    def get(self, request, *args, **kwargs):
        return Response()


class CustomTokenRefreshView(TokenRefreshView):
    """
    Refresh Token View: Extends SimpleJWT to allow GET requests (HTML Form).
    """
    def get(self, request, *args, **kwargs):
        return Response()
