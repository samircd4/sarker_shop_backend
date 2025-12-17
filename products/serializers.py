from rest_framework import serializers
from django.db import transaction
import json
from accounts.serializers import CustomerSerializer, AddressSerializer
from drf_spectacular.utils import extend_schema_field

from .models import (
    Category, Brand, Product, ProductImage, ProductSpecification,
    ProductVariant
)


###########################################################################


# --- Helper Serializers ---
class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image']


class ProductSpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSpecification
        fields = ['key', 'value']


class ProductVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = ['id', 'name', 'sku', 'price', 'stock_quantity', 'attributes']


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name', 'slug', 'logo']


class SubCategorySerializer(serializers.ModelSerializer):
    """Used to avoid infinite recursion when serializing category children"""
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'logo']


class CategorySerializer(serializers.ModelSerializer):
    children = SubCategorySerializer(many=True, read_only=True)
    breadcrumbs = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'logo',
                  'parent', 'children', 'breadcrumbs']

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_breadcrumbs(self, obj):
        return obj.get_breadcrumbs()

# --- 0. HELPER SERIALIZERS (To avoid circular imports) ---


class SimpleProductSerializer(serializers.ModelSerializer):
    """
    Used inside Orders and Reviews to show minimal product info.
    Prevents loading the full product details (specs, all images) unnecessarily.
    """
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'wholesale_price', 'image', 'slug']

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_image(self, obj):
        # Return full URL of the main image
        if obj.image:
            return obj.image.url
        return None


# --- Main Product Serializer ---


class ProductSerializer(serializers.ModelSerializer):
    # Read-only nested fields (for display)
    brand = BrandSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    gallery_images = ProductImageSerializer(many=True, read_only=True)
    specifications = ProductSpecificationSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    related_products = SimpleProductSerializer(many=True, read_only=True)

    # Write-only fields (for input)
    brand_id = serializers.PrimaryKeyRelatedField(
        queryset=Brand.objects.all(), source='brand', write_only=True
    )
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
    )
    related_products_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Product.objects.all(), source='related_products', write_only=True, required=False
    )

    # Special field to accept multiple images (Write Only)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(allow_empty_file=False, use_url=False),
        write_only=True,
        required=False
    )

    # Special field to accept specs as a JSON string (easier for React/Postman)
    specs_input = serializers.JSONField(write_only=True, required=False)

    # Special field for variants input
    variants_input = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = Product
        fields = [
            'id', 'product_id', 'sku', 'name', 'slug',
            'description', 'short_description',
            'price', 'wholesale_price', 'discount_price',
            'brand', 'brand_id',
            'category', 'category_id',
            'image',            # Main cover image
            'uploaded_images',  # Gallery images (Input)
            'gallery_images',   # Gallery images (Output)
            'specs_input',      # Specs (Input)
            'specifications',   # Specs (Output)
            'variants_input',   # Variants (Input)
            'variants',         # Variants (Output)
            'related_products_ids',  # Related (Input)
            'related_products',  # Related (Output)
            'rating', 'reviews_count', 'stock_quantity',
            'is_featured', 'is_bestseller', 'is_active', 'created_at', 'updated_at',
        ]

    def create(self, validated_data):
        # 1. Pop (remove) the nested data that isn't part of the Product model
        uploaded_images = validated_data.pop('uploaded_images', [])
        specs_input = validated_data.pop('specs_input', [])
        variants_input = validated_data.pop('variants_input', [])
        related_products = validated_data.pop('related_products', [])

        # 2. Create the Main Product
        product = Product.objects.create(**validated_data)

        # Set related products
        if related_products:
            product.related_products.set(related_products)

        # 3. Create Gallery Images
        for image in uploaded_images:
            ProductImage.objects.create(product=product, image=image)

        # 4. Create Specifications
        if specs_input:
            if isinstance(specs_input, str):
                try:
                    specs_input = json.loads(specs_input)
                except ValueError:
                    specs_input = []

            for spec in specs_input:
                ProductSpecification.objects.create(
                    product=product,
                    key=spec.get('key'),
                    value=spec.get('value')
                )

        # 5. Create Variants
        if variants_input:
            if isinstance(variants_input, str):
                try:
                    variants_input = json.loads(variants_input)
                except ValueError:
                    variants_input = []

            for variant_data in variants_input:
                ProductVariant.objects.create(product=product, **variant_data)

        return product


# --- 1. CUSTOMER & PROFILE ---
# Moved to accounts app

# --- 2. ADDRESS BOOK ---
# Moved to accounts app


# --- 3. REVIEWS ---
# Moved to reviews app
