from django.contrib import admin
# from django.forms.models import BaseInlineFormSet
from .models import (
    Category, Brand, Product, ProductImage, ProductSpecification,
    ProductVariant
)

# --- Inlines (Manage these inside the Product Page) ---


class ProductSpecificationInline(admin.TabularInline):
    model = ProductSpecification
    extra = 1
    autocomplete_fields = ['product']


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'alt_text', 'is_primary', 'order')


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 0
    fields = ('sku', 'price', 'wholesale_price', 'discount_price',
              'stock_quantity', 'ram', 'storage', 'color', 'is_active')
    readonly_fields = ('sku',)


# --- Main Admin Classes ---


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'product_id',
        'brand',
        'category',
        'display_price',
        'display_stock',
        'is_active',
        'is_featured',
        'is_bestseller'
    )

    list_filter = (
        'brand',
        'category',
        'is_active',
        'is_featured',
        'is_bestseller',
        'created_at'
    )

    search_fields = ('name', 'product_id', 'sku')

    readonly_fields = (
        'product_id',
        'slug',
        'sku',
        'created_at',
        'updated_at'
    )

    inlines = [
        ProductSpecificationInline,
        ProductImageInline,
        ProductVariantInline,
    ]

    fieldsets = (
        ('Identification', {
            'fields': ('name', 'slug', 'product_id', 'sku')
        }),
        ('Relationships', {
            'fields': ('brand', 'category', 'related_products')
        }),
        ('Pricing (Non-Variant Only)', {
            'fields': ('price',),
            'description': 'Used only if the product has NO variants'
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured', 'is_bestseller')
        }),
        ('Media & Content', {
            'fields': ('image', 'short_description', 'description')
        }),
        ('Social Proof', {
            'fields': ('rating', 'reviews_count')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    filter_horizontal = ('related_products',)

    @admin.display(description="Price")
    def display_price(self, obj):
        if obj.variants.exists():
            return "Variant Based"
        return obj.price

    @admin.display(description="Stock")
    def display_stock(self, obj):
        if obj.variants.exists():
            return sum(v.stock_quantity for v in obj.variants.all())
        return 0


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent')
    search_fields = ('name',)
    readonly_fields = ('slug',)  # Auto-generated


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    readonly_fields = ('slug',)  # Auto-generated


# --- 4. REVIEW ADMIN ---
# Moved to reviews app
