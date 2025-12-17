from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save, post_delete
from django.utils.text import slugify
from django.dispatch import receiver
from django.db.models import Avg
from django.db import models
from decimal import Decimal
import random

from accounts.models import Customer


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    logo = models.ImageField(upload_to='categories/', blank=True, null=True)
    parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='children')

    class Meta:
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_breadcrumbs(self):
        breadcrumbs = []
        category = self
        while category:
            breadcrumbs.insert(
                0, {'id': category.id, 'name': category.name, 'slug': category.slug})
            category = category.parent
        return breadcrumbs

    def __str__(self):
        full_path = [self.name]
        parent = self.parent
        while parent:
            full_path.insert(0, parent.name)
            parent = parent.parent
        return ' -> '.join(full_path)


class Brand(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True, blank=True)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    # --- 1. Identity ---
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)

    # Public ID: SS123456 (Auto-generated)
    product_id = models.CharField(max_length=20, unique=True, editable=False)

    # SKU: Manual entry, simple string (e.g. "IPHONE-15-PRO-BLK")
    sku = models.CharField(max_length=50, unique=True, blank=True)

    # --- 2. Relationships ---
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name='products')
    brand = models.ForeignKey(
        Brand, on_delete=models.CASCADE, related_name='products')
    related_products = models.ManyToManyField(
        'self', blank=True, symmetrical=False, related_name='related_to')

    # --- 3. Pricing ---
    price = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Retail Price")
    wholesale_price = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Wholesale Price")
    discount_price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True)

    # --- 4. Inventory & Status ---
    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_bestseller = models.BooleanField(
        default=False, help_text="Manual override for bestseller status")

    # --- 5. Media & Content ---
    # This is the "Cover Image" / Thumbnail for fast loading on the home page
    image = models.ImageField(upload_to='products/',
                              help_text='Cover image for the product card',
                              blank=True, null=True)

    short_description = models.TextField(
        blank=True, max_length=160, help_text="Shown in product lists")
    description = models.TextField(blank=True)

    # --- 6. Social Proof ---
    rating = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(5.0)], default=0.0)
    reviews_count = models.PositiveIntegerField(default=0)

    # --- 7. Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # 1. Auto-Slug
        if not self.slug:
            self.slug = slugify(self.name)
            original_slug = self.slug
            counter = 1
            while Product.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1

        # 2. Auto-Generate Product ID (SS + 6 Digits)
        if not self.product_id:
            while True:
                new_id = f"SS{random.randint(100000, 999999)}"
                if not Product.objects.filter(product_id=new_id).exists():
                    self.product_id = new_id
                    break

        # 3. Handle Empty SKU (Optional: make it same as slug or random if empty)
        if not self.sku:
            self.sku = self.product_id  # Fallback: use the SS-ID as SKU if user forgets

        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.product_id}] {self.name}"


class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='variants')
    name = models.CharField(
        max_length=100, help_text="e.g. Size: L, Color: Red")
    sku = models.CharField(max_length=50, unique=True, blank=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True, help_text="Override base price if set")
    stock_quantity = models.PositiveIntegerField(default=0)
    attributes = models.JSONField(
        default=dict, blank=True, help_text="Key-value attributes")

    def __str__(self):
        return f"{self.product.name} - {self.name}"


class ProductSpecification(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='specifications')
    key = models.CharField(max_length=50)   # e.g. "Color"
    value = models.CharField(max_length=50)  # e.g. "Red"

    def __str__(self):
        return f"{self.key}: {self.value}"


class ProductImage(models.Model):
    # This is for the Gallery (Multiple images per product)
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ImageField(upload_to='products/gallery/')

    def __str__(self):
        return f"Gallery Image for {self.product.product_id}"


# --- 4. Reviews ---
# Moved to reviews app

# --- SIGNALS ---
