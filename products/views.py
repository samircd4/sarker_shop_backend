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
from django.db.models import Count, Avg, Q
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from .models import (
    Product, Category, Brand,
    ProductVariant
)
from .serializers import (
    ProductSerializer, CategorySerializer, BrandSerializer
)
from accounts.models import Customer, Address
from accounts.serializers import CustomerSerializer, AddressSerializer

# ------------------------------------------------------------------
# Custom Permissions
# ------------------------------------------------------------------
# IsReviewOwnerOrReadOnly moved to reviews app


# ------------------------------------------------------------------
# Catalog ViewSets (Public Read, Admin Write)
# ------------------------------------------------------------------

@extend_schema(tags=['Catalog'])
class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all() \
        .select_related('brand', 'category') \
        .prefetch_related('gallery_images', 'specifications', 'variants', 'related_products')

    serializer_class = ProductSerializer

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter
    ]
    filterset_fields = {
        'category': ['exact'],
        'brand': ['exact'],
        'is_featured': ['exact'],
        'is_bestseller': ['exact'],
        'is_active': ['exact'],
        'price': ['gte', 'lte'],
    }
    search_fields = ['name', 'description', 'sku',
                     'product_id', 'brand__name', 'category__name']
    ordering_fields = ['price', 'created_at', 'rating', 'reviews_count']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]

    @extend_schema(
        summary="Suggest Products",
        description="Autocomplete suggestions for search bar.",
        parameters=[
            OpenApiParameter("search", OpenApiTypes.STR,
                             description="Search term")
        ],
        responses={200: OpenApiTypes.OBJECT}
    )
    @action(detail=False, methods=['get'])
    def suggest(self, request):
        """
        Autocomplete suggestions for search bar
        """
        query = request.query_params.get('search', '')
        if not query:
            return Response([])
        # Search by name or sku
        products = self.get_queryset().filter(
            Q(name__icontains=query) | Q(sku__icontains=query)
        )[:10]
        suggestions = [{'id': p.id, 'name': p.name, 'slug': p.slug}
                       for p in products]
        return Response(suggestions)

    @extend_schema(
        summary="Search Products",
        description="Search products by 'q' query parameter.",
        parameters=[
            OpenApiParameter("q", OpenApiTypes.STR, description="Search query")
        ],
        responses={200: ProductSerializer(many=True)}
    )
    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Search products by 'q' query parameter.
        """
        query = request.query_params.get('q', '')
        if not query:
            return Response([])

        results = self.get_queryset().filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(sku__icontains=query) |
            Q(brand__name__icontains=query) |
            Q(category__name__icontains=query)
        ).distinct()

        page = self.paginate_queryset(results)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(results, many=True)
        return Response(serializer.data)

    @extend_schema(summary="Featured Products")
    @action(detail=False, methods=['get'])
    def featured(self, request):
        featured = self.filter_queryset(
            self.get_queryset().filter(is_featured=True))
        page = self.paginate_queryset(featured)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(featured, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Bestselling Products",
        description="Returns products explicitly marked as 'is_bestseller' in the database."
    )
    @action(detail=False, methods=['get'])
    def bestsellers(self, request):
        """
        Returns products explicitly marked as 'is_bestseller' in the database.
        """
        bestsellers = self.get_queryset().filter(is_bestseller=True)

        page = self.paginate_queryset(bestsellers)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(bestsellers, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Related Products",
        description="Returns related products based on manual selection or category."
    )
    @action(detail=True, methods=['get'])
    def related(self, request, pk=None):
        """
        Returns related products based on:
        1. Manual 'related_products'
        2. Same category (fallback)
        """
        product = self.get_object()

        # 1. Manual
        related = product.related_products.all()

        # 2. If few manual, add same category
        if related.count() < 4:
            same_category = Product.objects.filter(category=product.category) \
                .exclude(id=product.id) \
                .exclude(id__in=related.values_list('id', flat=True)) \
                .order_by('?')[:4]  # Random 4
            related = related | same_category
            related = related.distinct()

        serializer = self.get_serializer(related, many=True)
        return Response(serializer.data)


@extend_schema(tags=['Catalog'])
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['name']
    filterset_fields = ['parent']  # Allows filtering by parent=null for roots

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]

    @extend_schema(
        summary="Root Categories",
        description="Return only top-level categories."
    )
    @action(detail=False, methods=['get'])
    def roots(self, request):
        """Return only top-level categories"""
        roots = self.queryset.filter(parent__isnull=True)
        serializer = self.get_serializer(roots, many=True)
        return Response(serializer.data)


@extend_schema(tags=['Catalog'])
class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all()
    serializer_class = BrandSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [AllowAny()]


# ------------------------------------------------------------------
# Customer Profile (Authenticated)
# Moved to accounts app
# ------------------------------------------------------------------

# ------------------------------------------------------------------
# Address (Authenticated, Own Only)
# Moved to accounts app
# ------------------------------------------------------------------


# ------------------------------------------------------------------
# Orders (Authenticated, Own Only)
# Moved to orders app
# ------------------------------------------------------------------


# ------------------------------------------------------------------
# Reviews (Public Read, Auth Write, Owner Edit)
# Moved to reviews app
# ------------------------------------------------------------------
