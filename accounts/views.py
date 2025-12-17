from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from .models import Customer, Address
from .serializers import (
    RegisterSerializer, CustomerSerializer, AddressSerializer,
    ChangePasswordSerializer, LogoutSerializer, ForgotPasswordSerializer, ResetPasswordSerializer
)
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

# --- Auth Views ---


class RegisterView(generics.CreateAPIView):
    """
    Handles user registration.
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Register a new user",
        description="Creates a new user account with the provided information.",
        responses={201: RegisterSerializer}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    @extend_schema(exclude=True)
    def get(self, request, *args, **kwargs):
        # This returns an empty response, which DRF renders as the HTML Form
        return Response()


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Login View: Extends SimpleJWT.
    """
    @extend_schema(
        summary="Obtain JWT Pair",
        description="Takes a set of user credentials and returns an access and refresh JSON web token pair to prove the authentication of those credentials.",
        responses={200: OpenApiTypes.OBJECT}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    @extend_schema(exclude=True)
    def get(self, request, *args, **kwargs):
        return Response()


class CustomTokenRefreshView(TokenRefreshView):
    """
    Refresh Token View: Extends SimpleJWT.
    """
    @extend_schema(
        summary="Refresh JWT Token",
        description="Takes a refresh type JSON web token and returns an access type JSON web token if the refresh token is valid.",
        responses={200: OpenApiTypes.OBJECT}
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    @extend_schema(exclude=True)
    def get(self, request, *args, **kwargs):
        return Response()


class ChangePasswordView(generics.UpdateAPIView):
    """
    An endpoint for changing password.
    """
    serializer_class = ChangePasswordSerializer
    model = User
    permission_classes = (IsAuthenticated,)

    def get_object(self, queryset=None):
        return self.request.user

    @extend_schema(
        summary="Change Password",
        description="Change the password for the authenticated user.",
        request=ChangePasswordSerializer,
        responses={200: OpenApiTypes.OBJECT}
    )
    def update(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            # Check old password
            if not self.object.check_password(serializer.data.get("old_password")):
                return Response({"old_password": ["Wrong password."]}, status=status.HTTP_400_BAD_REQUEST)

            # set_password also hashes the password that the user will get
            self.object.set_password(serializer.data.get("new_password"))
            self.object.save()

            return Response({"status": "success", "message": "Password updated successfully"}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = LogoutSerializer

    @extend_schema(
        summary="Logout",
        description="Blacklist the refresh token to logout the user.",
        request=LogoutSerializer,
        responses={205: None}
    )
    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class ForgotPasswordView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ForgotPasswordSerializer

    @extend_schema(
        summary="Forgot Password",
        description="Request a password reset link to be sent to the email address.",
        request=ForgotPasswordSerializer,
        responses={200: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        # Stub implementation
        email = request.data.get('email')
        if not email:
            return Response({"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST)
        # In a real app, send email with reset token
        return Response({"message": "If the email exists, a reset link has been sent."}, status=status.HTTP_200_OK)


class ResetPasswordView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ResetPasswordSerializer

    @extend_schema(
        summary="Reset Password",
        description="Reset the password using the token received in email.",
        request=ResetPasswordSerializer,
        responses={200: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        # Stub implementation
        return Response({"message": "Password reset successfully"}, status=status.HTTP_200_OK)

# --- Profile Views ---


@extend_schema(tags=['Accounts'])
class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'put', 'patch']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Customer.objects.none()
        if self.request.user.is_staff:
            return Customer.objects.all()
        return Customer.objects.filter(user=self.request.user)

    @extend_schema(
        summary="Get Current Customer Profile",
        description="Retrieve the profile of the currently authenticated user.",
        responses={200: CustomerSerializer}
    )
    @action(detail=False, methods=['get', 'put'], permission_classes=[IsAuthenticated])
    def me(self, request):
        customer = get_object_or_404(Customer, user=request.user)

        if request.method == 'GET':
            serializer = self.get_serializer(customer)
            return Response(serializer.data)

        serializer = self.get_serializer(
            customer, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


@extend_schema(tags=['Accounts'])
class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Address.objects.none()
        return Address.objects.filter(customer__user=self.request.user)

    @extend_schema(
        summary="Set Default Address",
        description="Set the specified address as the default address for the customer.",
        request=None,
        responses={200: OpenApiTypes.OBJECT}
    )
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        address = self.get_object()
        # Set all other addresses to not default
        Address.objects.filter(
            customer=address.customer).update(is_default=False)
        address.is_default = True
        address.save()
        return Response({'status': 'default address set'})
