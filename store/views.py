from rest_framework import viewsets, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAdminUser,
    BasePermission,
    SAFE_METHODS,
)
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404

from .models import (
    Product, Category, Brand,
    Customer, Address, Order, Review
)
from .serializers import (
    ProductSerializer, CategorySerializer, BrandSerializer,
    CustomerSerializer, AddressSerializer, OrderSerializer, ReviewSerializer
)

# ------------------------------------------------------------------
# Custom Permissions
# ------------------------------------------------------------------

class IsReviewOwnerOrReadOnly(BasePermission):
    """
    Review owners can edit/delete their reviews.
    Admins can edit/delete all.
    Everyone can read.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.user == request.user or request.user.is_staff


# ------------------------------------------------------------------
# API Root (PUBLIC)
# ------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request, format=None):
    return Response({
        # Catalog
        'products': reverse('product-list', request=request, format=format),
        'categories': reverse('category-list', request=request, format=format),
        'brands': reverse('brand-list', request=request, format=format),

        # Customer
        'profile': reverse('customer-list', request=request, format=format),
        'addresses': reverse('address-list', request=request, format=format),
        'orders': reverse('order-list', request=request, format=format),

        # Social
        'reviews': reverse('review-list', request=request, format=format),

        # Auth
        'register': reverse('auth_register', request=request, format=format),
        'login': reverse('token_obtain_pair', request=request, format=format),
    })


# ------------------------------------------------------------------
# Catalog ViewSets (Public Read, Admin Write)
# ------------------------------------------------------------------

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all() \
        .select_related('brand', 'category') \
        .prefetch_related('gallery_images', 'specifications')

    serializer_class = ProductSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_fields = ['category', 'brand', 'is_featured', 'is_active']
    search_fields = ['name', 'description', 'sku', 'product_id']
    ordering_fields = ['price', 'created_at', 'rating']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]


class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]


# ------------------------------------------------------------------
# Customer Profile (Authenticated)
# ------------------------------------------------------------------

class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'put', 'patch']

    def get_queryset(self):
        if self.request.user.is_staff:
            return Customer.objects.all()
        return Customer.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get', 'put'], permission_classes=[IsAuthenticated])
    def me(self, request):
        customer = get_object_or_404(Customer, user=request.user)

        if request.method == 'GET':
            serializer = self.get_serializer(customer)
            return Response(serializer.data)

        serializer = self.get_serializer(customer, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# ------------------------------------------------------------------
# Address (Authenticated, Own Only)
# ------------------------------------------------------------------

class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(customer__user=self.request.user)


# ------------------------------------------------------------------
# Orders (Authenticated, Own Only)
# ------------------------------------------------------------------

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['order_status', 'is_paid']
    ordering_fields = ['created_at', 'total_amount']

    def get_queryset(self):
        if self.request.user.is_staff:
            return Order.objects.all()
        return Order.objects.filter(customer__user=self.request.user)


# ------------------------------------------------------------------
# Reviews (Public Read, Auth Write, Owner Edit)
# ------------------------------------------------------------------

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsReviewOwnerOrReadOnly]

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['product', 'rating']
    ordering_fields = ['created_at', 'rating']

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
