from rest_framework import serializers
from .models import Category, Product, ProductImage


class ProductImageSerializer(serializers.ModelSerializer):
    """Serializer for product additional images."""
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'order']


class SubCategorySerializer(serializers.ModelSerializer):
    """Used for nested subcategories."""
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug']


class CategorySerializer(serializers.ModelSerializer):
    """Category with optional subcategories."""
    subcategories = SubCategorySerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description',
                  'image', 'parent', 'subcategories']


class ProductSerializer(serializers.ModelSerializer):
    """Product serializer with nested category and additional images."""
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
    )
    additional_images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'price',
            'category',
            'category_id',
            'image',
            'additional_images',
            'rating',
            'reviews_count',
            'is_featured',
            'specifications',
            'stock',
            'created_at',
            'updated_at',
        ]
