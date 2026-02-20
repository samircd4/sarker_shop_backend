from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from rest_framework import generics, permissions, status, viewsets, views
from rest_framework.response import Response
from rest_framework.decorators import action
from django.templatetags.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from email.mime.image import MIMEImage
import os

def attach_logo(email_message):
    """
    Attaches the brand logo to an EmailMessage for CID embedding.
    """
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
    if os.path.exists(logo_path):
        try:
            with open(logo_path, 'rb') as f:
                logo_data = f.read()
                logo_image = MIMEImage(logo_data)
                logo_image.add_header('Content-ID', '<logo_image>')
                email_message.attach(logo_image)
        except Exception:
            pass # Fallback to no logo if file is missing or corrupted

from .models import Customer, Address, Division, District, SubDistrict
from .serializers import (
    RegisterSerializer, CustomerSerializer,
    AddressSerializer, DivisionSerializer, DistrictSerializer, SubDistrictSerializer,
    ChangePasswordSerializer, LogoutSerializer, ForgotPasswordSerializer, ResetPasswordSerializer,
    ResendVerificationEmailSerializer,
    CustomTokenObtainPairSerializer,
)
from drf_spectacular.utils import extend_schema, OpenApiTypes
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.facebook.views import FacebookOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from allauth.account.models import EmailAddress

# --- Auth Views ---

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client
    callback_url = settings.FRONTEND_URL  # Read from FRONTEND_URL in .env

class FacebookLogin(SocialLoginView):
    adapter_class = FacebookOAuth2Adapter

from allauth.socialaccount.providers.oauth2.client import OAuth2Client


from orders.models import Order

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
        response = super().post(request, *args, **kwargs)
        
        # Check for order linking
        link_order_id = request.data.get('link_order_id')
        if response.status_code == 201:
            try:
                # 1. Get the created user
                email = request.data.get('email')
                user = User.objects.get(email=email)
                
                # 2. Create EmailAddress (Unverified) for Allauth/Admin compatibility
                from allauth.account.models import EmailAddress
                EmailAddress.objects.get_or_create(user=user, email=email, defaults={'verified': False, 'primary': True})

                # 3. Send Verification Email (Manual)
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                
                frontend_url = settings.FRONTEND_URL
                verify_link = f"{frontend_url}/verify-email/?uid={uid}&token={token}"
                
                full_name = request.data.get('full_name', 'User')
                
                # Render HTML Template
                from django.template.loader import render_to_string
                from django.utils.html import strip_tags
                from django.core.mail import EmailMultiAlternatives

                html_content = render_to_string('emails/welcome_email.html', {
                    'full_name': full_name,
                    'verify_link': verify_link,
                })
                text_content = strip_tags(html_content)

                email_message = EmailMultiAlternatives(
                    subject="Welcome to Sarker Shop!",
                    body=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[email]
                )
                email_message.attach_alternative(html_content, "text/html")
                attach_logo(email_message)
                email_message.send(fail_silently=True)

                # 4. Check for order linking
                link_order_id = request.data.get('link_order_id')
                if link_order_id:
                    order = Order.objects.get(id=link_order_id)
                    if order.email == user.email and order.customer is None:
                        if hasattr(user, 'customer'):
                            order.customer = user.customer
                            order.save()
            except Exception as e:
                print(f"Post-register error: {e}")
                
        return response

    @extend_schema(exclude=True)
    def get(self, request, *args, **kwargs):
        # This returns an empty response, which DRF renders as the HTML Form
        return Response()


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Login View: Extends SimpleJWT.
    """
    serializer_class = CustomTokenObtainPairSerializer

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
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email)
            
            # Generate token and uid
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            
            # Build reset link (Frontend URL)
            # Frontend URL from .env
            frontend_url = settings.FRONTEND_URL
            reset_link = f"{frontend_url}/password-reset-confirm/?uid={uid}&token={token}"
            
            # Render HTML Template
            from django.template.loader import render_to_string
            from django.utils.html import strip_tags
            from django.core.mail import EmailMultiAlternatives

            html_content = render_to_string('emails/password_reset_email.html', {
                'user': user,
                'reset_link': reset_link,
            })
            text_content = strip_tags(html_content)

            email_message = EmailMultiAlternatives(
                subject="Password Reset Request",
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email]
            )
            email_message.attach_alternative(html_content, "text/html")
            attach_logo(email_message)
            email_message.send(fail_silently=False)
            
        except User.DoesNotExist:
            return Response({"error": "Email is not associated with any account."}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Password reset link has been sent to your email."}, status=status.HTTP_200_OK)


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
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Determine user from validated data (serializer set it)
        user = serializer.validated_data['user']
        new_password = serializer.validated_data['new_password']
        
        user.set_password(new_password)
        user.save()
        
        return Response({"message": "Password reset successfully"}, status=status.HTTP_200_OK)


class VerifyEmailView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    # Reuse ResetPasswordSerializer logic for uid/token validation or create a new one
    # We can handle it manually here to avoid creating another serializer just for this
    
    @extend_schema(
        summary="Verify Email",
        description="Verify email using uid and token.",
        request=None, 
        parameters=[
            OpenApiTypes.STR, OpenApiTypes.STR # loosely defined, usually query params?
        ],
        responses={200: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        uidb64 = request.data.get('uidb64')
        token = request.data.get('token')
        
        if not uidb64 or not token:
            return Response({"error": "Missing uid or token"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({"error": "Invalid UID"}, status=status.HTTP_400_BAD_REQUEST)

        if default_token_generator.check_token(user, token):
            # Mark verified
            # We can create/update EmailAddress from allauth
            from allauth.account.models import EmailAddress
            email_address, created = EmailAddress.objects.get_or_create(user=user, email=user.email)
            email_address.verified = True
            email_address.primary = True
            email_address.save()
            
            return Response({"message": "Email verified successfully"}, status=status.HTTP_200_OK)
        
        return Response({"error": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)




class ResendVerificationEmailView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ResendVerificationEmailSerializer

    @extend_schema(
        summary="Resend Verification Email",
        description="Admin or authenticated user can supply any email address to resend the verification link.",
        responses={200: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"error": "No account found with this email address."}, status=status.HTTP_404_NOT_FOUND)

        # Ensure EmailAddress object exists
        from allauth.account.models import EmailAddress
        email_address, created = EmailAddress.objects.get_or_create(
            user=user, email=user.email,
            defaults={'verified': False, 'primary': True}
        )

        if email_address.verified and not request.user.is_staff:
            return Response({"message": "Email is already verified."}, status=status.HTTP_200_OK)

        # Build verification link
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        frontend_url = settings.FRONTEND_URL
        verify_link = f"{frontend_url}/verify-email/?uid={uid}&token={token}"

        # Render HTML Template
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags
        from django.core.mail import EmailMultiAlternatives

        html_content = render_to_string('emails/verification_email.html', {
            'full_name': getattr(user, 'customer', None).name if hasattr(user, 'customer') else user.username,
            'verify_link': verify_link,
        })
        text_content = strip_tags(html_content)

        print(f"Sending verification email to {user.email}...")
        try:
            email_message = EmailMultiAlternatives(
                subject="Verify Your Email Address",
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            email_message.attach_alternative(html_content, "text/html")
            attach_logo(email_message)
            email_message.send(fail_silently=False)
            print(f"Verification email sent to {user.email}")
        except Exception as e:
            print(f"Failed to send verification email: {e}")
            return Response({"error": f"Failed to send email: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"message": f"Verification email sent to {email}."}, status=status.HTTP_200_OK)

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


# --- Location Views ---

@extend_schema(tags=['Locations'])
class DivisionViewSet(viewsets.ModelViewSet):
    """
    Manage Divisions.
    """
    queryset = Division.objects.all()
    serializer_class = DivisionSerializer
    pagination_class = None

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

@extend_schema(tags=['Locations'])
class DistrictViewSet(viewsets.ModelViewSet):
    """
    Manage Districts.
    Filter by division: ?division_id=X
    """
    serializer_class = DistrictSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = District.objects.all()
        division_id = self.request.query_params.get('division_id')
        if division_id:
            queryset = queryset.filter(division_id=division_id)
        return queryset

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

@extend_schema(tags=['Locations'])
class SubDistrictViewSet(viewsets.ModelViewSet):
    """
    Manage Sub-Districts.
    Filter by district: ?district_id=Y
    """
    serializer_class = SubDistrictSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = SubDistrict.objects.all()
        district_id = self.request.query_params.get('district_id')
        if district_id:
            queryset = queryset.filter(district_id=district_id)
        return queryset

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
