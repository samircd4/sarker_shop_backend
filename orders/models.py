from django.db import models
from django.conf import settings
from decimal import Decimal
from accounts.models import Customer, Address
from products.models import Product

# 1. Order Status Model


class OrderStatus(models.Model):
    """
    Tracks lifecycle states: Pending, Confirmed, Shipped, Delivered, Cancelled.
    """
    status_code = models.CharField(
        max_length=20, unique=True)  # e.g., 'pending'
    display_name = models.CharField(max_length=50)  # e.g., 'Pending'
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.display_name

# 2. Payment Info Model


class PaymentInfo(models.Model):
    """
    Stores payment transaction details.
    """
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    is_paid = models.BooleanField(default=False)
    payment_method = models.CharField(
        max_length=50, default='cod', help_text="e.g. 'stripe', 'cod'")
    payment_date = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.transaction_id or 'Pending'} - {'Paid' if self.is_paid else 'Unpaid'}"

# 3. Cart Model


class Cart(models.Model):
    """
    Shopping cart for session or user.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Cart {self.id} ({self.user.username if self.user else self.session_key})"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items',
                             on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

# 4. Checkout Model


class Checkout(models.Model):
    """
    Handles checkout process data.
    """
    cart = models.OneToOneField(Cart, on_delete=models.CASCADE)
    shipping_address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, blank=True, related_name='checkouts_shipping')
    billing_address = models.ForeignKey(
        Address, on_delete=models.SET_NULL, null=True, blank=True, related_name='checkouts_billing')
    email = models.EmailField(blank=True, null=True)  # For guest checkout
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Checkout {self.id}"

# 5. Order Model (Transferred)


class Order(models.Model):
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name='orders')
    address = models.ForeignKey(
        Address, on_delete=models.PROTECT, null=True, blank=True)

    total_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Linked to OrderStatus
    order_status = models.ForeignKey(
        OrderStatus, on_delete=models.PROTECT, null=True, blank=True)

    # Linked to PaymentInfo
    payment_info = models.OneToOneField(
        PaymentInfo, on_delete=models.PROTECT, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order #{self.id} - {self.customer.name}"

    def update_total_amount(self):
        self.total_amount = sum(item.subtotal for item in self.items.all())
        self.save(update_fields=['total_amount'])


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal('0.00'))

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if is_new and self.product:
            self.price = self.product.price
        super().save(*args, **kwargs)
        # update order total
        self.order.update_total_amount()

    def delete(self, *args, **kwargs):
        order = self.order
        super().delete(*args, **kwargs)
        order.update_total_amount()

    @property
    def subtotal(self):
        return self.price * self.quantity
