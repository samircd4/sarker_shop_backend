from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from smart_selects.db_fields import ChainedForeignKey

# --- Geolocation Models ---
class Division(models.Model):
    name = models.CharField(max_length=100, unique=True)
    bn_name = models.CharField(max_length=100, blank=True, null=True)
    lat = models.CharField(max_length=20, blank=True, null=True)
    long = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.name

class District(models.Model):
    division = models.ForeignKey(Division, on_delete=models.CASCADE, related_name='districts')
    name = models.CharField(max_length=100)
    bn_name = models.CharField(max_length=100, blank=True, null=True)
    lat = models.CharField(max_length=20, blank=True, null=True)
    long = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class SubDistrict(models.Model):
    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name='sub_districts')
    name = models.CharField(max_length=100)
    bn_name = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Sub-District (Upazila)"
        verbose_name_plural = "Sub-Districts (Upazilas)"

    def __str__(self):
        return self.name


class Customer(models.Model):
    CUSTOMER_TYPES = (
        ('retail', 'Retail Customer'),
        ('wholesale', 'Wholesale Customer'),
    )

    # Link to the Login User
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer')
    
    # Customer Details
    name = models.CharField(max_length=200, help_text="Full Name")
    email = models.EmailField(help_text="Contact Email", unique=True) # Can be different from User login email
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
    division = models.ForeignKey(Division, on_delete=models.PROTECT, null=True, blank=True)
    district = ChainedForeignKey(
        District,
        chained_field="division",
        chained_model_field="division",
        show_all=False,
        auto_choose=True,
        sort=True,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    sub_district = ChainedForeignKey(
        SubDistrict,
        chained_field="district",
        chained_model_field="district",
        show_all=False,
        auto_choose=True,
        sort=True,
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    address = models.TextField(help_text="House no. / Building / Street")
    
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
