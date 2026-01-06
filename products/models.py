from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from django.db import models
import random
from django.db.models import Min


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
        return str(self.name)


class Product(models.Model):
    PRODUCT_TYPE_CHOICES = (
        ("simple", "Simple"),
        ("variant", "Variant"),
    )

    # --- 1. Identity ---
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)

    # Public readable ID → SS123456
    product_id = models.CharField(
        max_length=20, unique=True, editable=False
    )

    # Auto-generated base SKU (used as prefix for variants)
    sku = models.CharField(
        max_length=50, unique=True, editable=False
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Used only for simple products"
    )

    product_type = models.CharField(
        max_length=10,
        choices=PRODUCT_TYPE_CHOICES,
        default="simple"
    )

    # --- 2. Relationships ---
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="products"
    )
    brand = models.ForeignKey(
        Brand, on_delete=models.CASCADE, related_name="products"
    )
    related_products = models.ManyToManyField(
        "self", blank=True, symmetrical=False
    )

    # --- 3. Media & Content ---
    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True,
        help_text="Main thumbnail"
    )

    short_description = models.TextField(
        blank=True, max_length=160
    )
    description = models.TextField(blank=True)

    # --- 4. Status & Flags ---
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    is_bestseller = models.BooleanField(default=False)

    # --- 5. Social Proof ---
    rating = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    reviews_count = models.PositiveIntegerField(default=0)

    # --- 6. Timestamps ---
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        # 1️⃣ Auto Slug
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug

        # 2️⃣ Auto Product ID (SS + 6 digits)
        if not self.product_id:
            while True:
                pid = f"SS{random.randint(100000, 999999)}"
                if not Product.objects.filter(product_id=pid).exists():
                    self.product_id = pid
                    break

        # 3️⃣ Auto SKU
        if not self.sku:
            self.sku = self.product_id

        super().save(*args, **kwargs)

    @property
    def display_price(self):
        """
        Returns:
        - Product.price for simple products
        - Minimum variant price for variant products
        """
        if self.variants.exists():
            return self.variants.aggregate(
                min_price=Min('price')
            )['min_price']
        return self.price

    @property
    def display_wholesale_price(self):
        """
        Returns:
        - Product.wholesale_price for simple products
        - Minimum variant wholesale_price for variant products
        """
        if self.variants.exists():
            return self.variants.aggregate(
                min_wholesale=Min('wholesale_price')
            )['min_wholesale']
        return getattr(self, 'wholesale_price', None)

    @property
    def display_discount_price(self):
        """
        Returns:
        - Product.discount_price if exists
        - Minimum variant discount_price if variants exist
        """
        if self.variants.exists():
            return self.variants.aggregate(
                min_discount=Min('discount_price')
            )['min_discount']
        return getattr(self, 'discount_price', None)

    def __str__(self):
        return f"{self.name} ({self.product_id})"


class ProductVariant(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants"
    )

    # Variant attributes (NULL for simple products)
    ram = models.PositiveIntegerField(null=True, blank=True)
    storage = models.PositiveIntegerField(null=True, blank=True)
    color = models.CharField(max_length=50, blank=True)

    # Auto-generated variant SKU
    sku = models.CharField(
        max_length=80, unique=True, editable=False
    )

    price = models.DecimalField(max_digits=10, decimal_places=2)
    wholesale_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    discount_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["product", "ram", "storage", "color"],
                name="unique_variant_combo"
            )
        ]

    def save(self, *args, **kwargs):
        if not self.sku:
            parts = [self.product.sku]

            if self.ram:
                parts.append(f"{self.ram}GB")
            if self.storage:
                parts.append(f"{self.storage}GB")
            if self.color:
                parts.append(slugify(self.color).upper())

            self.sku = "-".join(parts)

        super().save(*args, **kwargs)

    def __str__(self):
        if self.product.product_type == "simple":
            return f"{self.product.name} (Default)"
        return f"{self.product.name} | {self.ram}/{self.storage} | {self.color}"


class ProductSpecification(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='specifications'
    )

    key = models.CharField(
        max_length=50,
        help_text="e.g. RAM, Storage, Color, Battery"
    )
    value = models.CharField(
        max_length=100,
        help_text="e.g. 6GB, 128GB, Blue, 5000mAh"
    )

    class Meta:
        unique_together = ('product', 'key')
        ordering = ['key']

    def __str__(self):
        return f"{self.product.name} | {self.key}: {self.value}"


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='gallery_images'
    )
    image = models.ImageField(upload_to='products/gallery/')
    is_primary = models.BooleanField(default=False)
    alt_text = models.CharField(
        max_length=150,
        blank=True,
        help_text="SEO & accessibility text"
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Image for {self.product.name}"

    def save(self, *args, **kwargs):
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
