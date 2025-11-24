from .serializers import ProductSerializer
from .models import Product
from rest_framework import viewsets
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


# views.py


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    lookup_field = 'pk'  # or 'pk' if you use ID instead of slug

    def get_queryset(self):
        """
        Optimized queryset:
        - Always select the main category (ForeignKey)
        - Always prefetch additional images (reverse FK / related_name='additional_images')
        This works perfectly for both list and retrieve actions.
        """
        return Product.objects.all()\
            .select_related('category')\
            .prefetch_related('additional_images')
