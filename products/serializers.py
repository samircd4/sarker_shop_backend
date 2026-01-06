from rest_framework import serializers
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
        fields = [
            'id', 'sku', 'price', 'wholesale_price', 'discount_price',
            'stock_quantity', 'ram', 'storage', 'color', 'is_active'
        ]


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
    price = serializers.SerializerMethodField()
    wholesale_price = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'wholesale_price', 'image', 'slug']

    def get_price(self, obj):
        return obj.display_price

    def get_wholesale_price(self, obj):
        return obj.display_wholesale_price

    def get_image(self, obj):
        return obj.image.url if obj.image else None


# --- Main Product Serializer ---


class ProductSerializer(serializers.ModelSerializer):
    # ---------- READ ONLY DISPLAY ----------
    brand = BrandSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    gallery_images = ProductImageSerializer(many=True, read_only=True)
    specifications = ProductSpecificationSerializer(many=True, read_only=True)
    variants = ProductVariantSerializer(many=True, read_only=True)
    related_products = SimpleProductSerializer(many=True, read_only=True)

    price = serializers.SerializerMethodField(read_only=True)
    wholesale_price = serializers.SerializerMethodField()
    discount_price = serializers.SerializerMethodField()

    # ---------- WRITE ONLY INPUT ----------
    brand_id = serializers.PrimaryKeyRelatedField(
        queryset=Brand.objects.all(), source='brand', write_only=True
    )
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
    )
    related_products_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Product.objects.all(),
        source='related_products',
        write_only=True,
        required=False
    )

    uploaded_images = serializers.ListField(
        child=serializers.ImageField(allow_empty_file=False, use_url=False),
        write_only=True,
        required=False
    )

    specs_input = serializers.JSONField(write_only=True, required=False)
    variants_input = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = Product
        fields = [
            'id', 'product_id', 'sku', 'name', 'slug',
            'description', 'short_description',

            'price', 'wholesale_price', 'discount_price',

            'brand', 'brand_id',
            'category', 'category_id',

            'image',
            'uploaded_images',
            'gallery_images',

            'specs_input',
            'specifications',

            'variants_input',
            'variants',

            'related_products_ids',
            'related_products',

            'rating', 'reviews_count',
            'is_featured', 'is_bestseller', 'is_active',
            'created_at', 'updated_at',
        ]

    # ---------- PRICE LOGIC ----------
    def get_price(self, obj):
        discount = obj.display_discount_price
        if discount:
            return discount

        if obj.variants.exists():
            prices = obj.variants.exclude(
                price__isnull=True).values_list('price', flat=True)
            return min(prices) if prices else obj.price

        return obj.price

    def get_wholesale_price(self, obj):
        return obj.display_wholesale_price

    def get_discount_price(self, obj):
        return obj.display_discount_price

    # ---------- CREATE ----------
    def create(self, validated_data):
        uploaded_images = validated_data.pop('uploaded_images', [])
        specs_input = validated_data.pop('specs_input', [])
        variants_input = validated_data.pop('variants_input', [])
        related_products = validated_data.pop('related_products', [])

        product = Product.objects.create(**validated_data)

        if related_products:
            product.related_products.set(related_products)

        for image in uploaded_images:
            ProductImage.objects.create(product=product, image=image)

        for spec in specs_input or []:
            ProductSpecification.objects.create(
                product=product,
                key=spec.get('key'),
                value=spec.get('value')
            )

        for variant_data in variants_input or []:
            ProductVariant.objects.create(product=product, **variant_data)

        return product
