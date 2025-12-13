from django.urls import path, include
from rest_framework.routers import DefaultRouter

# 1. Import ViewSets and the API Root function
from .views import (
    CategoryViewSet, 
    ProductViewSet, 
    BrandViewSet, 
    CustomerViewSet,
    AddressViewSet,
    OrderViewSet,
    ReviewViewSet,
    api_root
)


# 2. Import your Custom Auth Views (which support the Web UI Form)
from .auth_views import (
    RegisterView, 
    CustomTokenObtainPairView, 
    CustomTokenRefreshView
)

# 3. Setup Router
router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'brands', BrandViewSet)
# User-scoped ViewSets (NO queryset → basename REQUIRED)
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'addresses', AddressViewSet, basename='address')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'reviews', ReviewViewSet)


# 4. Define URL Patterns
urlpatterns = [
    # Custom API Root (The "Home Page" with clickable links)
    path('', api_root, name='api-root'),

    # Business Endpoints (Products, etc.)
    path('', include(router.urls)),

    # Auth Endpoints (Using the Custom Views)
    path('auth/register/', RegisterView.as_view(), name='auth_register'),
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
]