from django.urls import path, include
from rest_framework.routers import DefaultRouter

# 1. Import ViewSets and the API Root function
from .views import (
    CategoryViewSet,
    ProductViewSet,
    BrandViewSet
)


# 3. Setup Router
router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'brands', BrandViewSet)


# 4. Define URL Patterns
urlpatterns = [
    # Business Endpoints (Products, etc.)
    path('', include(router.urls)),
]
