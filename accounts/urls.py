from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    ChangePasswordView,
    CustomerViewSet,
    AddressViewSet,
    LogoutView,
    ForgotPasswordView,
    ResetPasswordView,
    VerifyEmailView,
    ResendVerificationEmailView,
    DivisionViewSet,
    DistrictViewSet,
    SubDistrictViewSet,
    GoogleLogin,
    FacebookLogin
)

router = DefaultRouter()
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'addresses', AddressViewSet, basename='address')
router.register(r'divisions', DivisionViewSet, basename='division')
router.register(r'districts', DistrictViewSet, basename='district')
router.register(r'sub-districts', SubDistrictViewSet, basename='sub-district')

urlpatterns = [
    # Auth Endpoints
    path('auth/register/', RegisterView.as_view(), name='auth_register'),
    path('auth/login/', CustomTokenObtainPairView.as_view(),
         name='token_obtain_pair'),
    path('auth/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', LogoutView.as_view(), name='auth_logout'),
    path('auth/change-password/',
         ChangePasswordView.as_view(), name='change_password'),
    path('auth/forgot-password/',
         ForgotPasswordView.as_view(), name='forgot_password'),
    path('auth/reset-password/', ResetPasswordView.as_view(), name='reset_password'),
    path('auth/verify-email/', VerifyEmailView.as_view(), name='verify_email'),
    path('auth/resend-verification-email/', ResendVerificationEmailView.as_view(), name='resend_verification_email'),
    path('auth/google/', GoogleLogin.as_view(), name='google_login'),
    path('auth/facebook/', FacebookLogin.as_view(), name='facebook_login'),

    # Profile & Address Endpoints
    path('', include(router.urls)),
]
