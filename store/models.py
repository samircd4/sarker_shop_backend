from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models.signals import post_save, post_delete
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.dispatch import receiver
from django.db.models import Avg
from django.db import models
from decimal import Decimal
import random

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    logo = models.ImageField(upload_to='categories/', blank=True, null=True)
    
    class Meta:
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


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
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='products')

    # --- 3. Pricing ---
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Retail Price")
    wholesale_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Wholesale Price")
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    # --- 4. Inventory & Status ---
    stock_quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    # --- 5. Media & Content ---
    # This is the "Cover Image" / Thumbnail for fast loading on the home page
    image = models.ImageField(upload_to='products/', help_text='Cover image for the product card')
    
    short_description = models.TextField(blank=True, max_length=160, help_text="Shown in product lists")
    description = models.TextField(blank=True)
    
    # --- 6. Social Proof ---
    rating = models.FloatField(validators=[MinValueValidator(0.0), MaxValueValidator(5.0)],default=0.0)
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
            self.sku = self.product_id # Fallback: use the SS-ID as SKU if user forgets

        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.product_id}] {self.name}"


class ProductSpecification(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='specifications')
    key = models.CharField(max_length=50)   # e.g. "Color"
    value = models.CharField(max_length=50) # e.g. "Red"

    def __str__(self):
        return f"{self.key}: {self.value}"


class ProductImage(models.Model):
    # This is for the Gallery (Multiple images per product)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ImageField(upload_to='products/gallery/')
    
    def __str__(self):
        return f"Gallery Image for {self.product.product_id}"


class Customer(models.Model):
    CUSTOMER_TYPES = (
        ('retail', 'Retail Customer'),
        ('wholesale', 'Wholesale Customer'),
    )

    # Link to the Login User
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer')
    
    # Customer Details
    name = models.CharField(max_length=200, help_text="Full Name")
    email = models.EmailField(help_text="Contact Email") # Can be different from User login email
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    customer_type = models.CharField(max_length=20, choices=CUSTOMER_TYPES, default='retail')
    
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.customer_type})"

    @property
    def is_wholesaler(self):
        return self.customer_type == 'wholesale'


# --- 2. Address Book (Linked to Customer) ---
class Address(models.Model):
    ADDRESS_TYPES = (
        ('Home', 'Home'),
        ('Office', 'Office'),
    )

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='addresses')
    
    # 1. Contact Info (Specific to this delivery address)
    full_name = models.CharField(max_length=100, help_text="Receiver's Name")
    phone = models.CharField(max_length=20, help_text="Receiver's Phone")
    
    # 2. Location Details
    address = models.TextField(help_text="House no. / Building / Street")
    division = models.CharField(max_length=100)      # e.g. Dhaka
    district = models.CharField(max_length=100)      # e.g. Dhaka City
    sub_district = models.CharField(max_length=100)  # e.g. Dhanmondi / Upazila
    
    # 3. Preferences
    address_type = models.CharField(max_length=10, choices=ADDRESS_TYPES, default='Home')
    is_default = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # Ensure only one default address per customer
        if self.is_default:
            Address.objects.filter(customer=self.customer, is_default=True).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.address_type}: {self.full_name} ({self.sub_district})"


# --- 3. Order System (Linked to Customer) ---
class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )

    customer = models.ForeignKey(Customer,on_delete=models.CASCADE,related_name='orders')
    address = models.ForeignKey(Address,on_delete=models.PROTECT,null=True,blank=True)

    total_amount = models.DecimalField(max_digits=12,decimal_places=2,default=Decimal('0.00'))
    order_status = models.CharField(max_length=20,choices=STATUS_CHOICES,default='pending')
    is_paid = models.BooleanField(default=False)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.customer.name}"

    # 🔥 THIS IS THE KEY PART
    def update_total_amount(self):
        self.total_amount = sum(
            item.subtotal for item in self.items.all()
        )
        self.save(update_fields=['total_amount'])


class OrderItem(models.Model):
    order = models.ForeignKey(Order,on_delete=models.CASCADE,related_name='items')
    product = models.ForeignKey('Product',on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=12,decimal_places=2,default=Decimal('0.00'))

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        if is_new and self.product:
            self.price = self.product.price

        super().save(*args, **kwargs)

        # ✅ update order total AFTER save
        self.order.update_total_amount()

    def delete(self, *args, **kwargs):
        order = self.order
        super().delete(*args, **kwargs)
        order.update_total_amount()

    @property
    def subtotal(self):
        return self.price * self.quantity


# --- 4. Reviews ---
class Review(models.Model):
    product = models.ForeignKey('Product', on_delete=models.CASCADE, related_name='reviews')
    # Changed: Linked to Customer
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'customer')

    def __str__(self):
        return f"{self.rating}★ - {self.customer.name}"


# --- SIGNALS ---

@receiver(post_save, sender=User)
def create_customer_profile(sender, instance, created, **kwargs):
    if created:
        # Auto-create Customer, filling email/name from User
        Customer.objects.create(
            user=instance,
            name=instance.username,
            email=instance.email
        )

@receiver(post_save, sender=User)
def save_customer_profile(sender, instance, **kwargs):
    # Ensure customer exists before saving
    if hasattr(instance, 'customer'):
        instance.customer.save()

@receiver([post_save, post_delete], sender=Review)
def update_product_rating(sender, instance, **kwargs):
    product = instance.product
    aggregate_data = Review.objects.filter(product=product).aggregate(
        avg_rating=Avg('rating'),
        count=models.Count('id')
    )
    product.rating = aggregate_data['avg_rating'] or 0.0
    product.reviews_count = aggregate_data['count'] or 0
    product.save()