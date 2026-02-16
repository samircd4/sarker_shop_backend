from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Customer, Address, Division, District, SubDistrict
from allauth.account.models import EmailAddress

# --- 1. CUSTOMER ADMIN ---


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    # Now you can see Email and Phone directly in the list
    list_display = ('name', 'email', 'is_email_verified', 'phone_number', 'customer_type', 'avatar', 'user')
    list_editable = ('is_email_verified',)
    list_filter = ('customer_type', 'is_email_verified', 'created_at')
    search_fields = ('name', 'email', 'phone_number', 'user__username')

    # You can also edit the user link if needed, but usually read-only
    raw_id_fields = ('user',)

    # Remove the custom method since we now have a real field
    # actions are still useful for bulk updates
    actions = ['mark_verified', 'mark_unverified']

    @admin.action(description='Mark selected customers as Verified')
    def mark_verified(self, request, queryset):
        count = 0
        for customer in queryset:
            email_address, created = EmailAddress.objects.get_or_create(
                user=customer.user, 
                email=customer.user.email,
                defaults={'verified': False, 'primary': True}
            )
            if not email_address.verified:
                email_address.verified = True
                email_address.save()
                count += 1
        self.message_user(request, f"{count} customers marked as verified.")

    @admin.action(description='Mark selected customers as Unverified')
    def mark_unverified(self, request, queryset):
        count = 0
        for customer in queryset:
            # We only update if it exists, we don't necessarily need to create if unverifying?
            # But consistent behavior is good.
            email_address = EmailAddress.objects.filter(user=customer.user, email=customer.user.email).first()
            if email_address and email_address.verified:
                email_address.verified = False
                email_address.save()
                count += 1
        self.message_user(request, f"{count} customers marked as unverified.")


# --- 2. ADDRESS ADMIN ---
@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    # Columns to show in the list
    list_display = ('customer', 'full_name', 'phone', 'address_type',
                    'division', 'district', 'sub_district', 'is_default')

    # Filters on the right side
    list_filter = ('division', 'address_type', 'is_default')

    # Search bar
    search_fields = ('full_name', 'phone', 'address', 'customer__name')


# --- 3. LOCATION ADMIN ---
@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    list_display = ('name', 'bn_name', 'lat', 'long')
    search_fields = ('name', 'bn_name')

@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ('name','bn_name', 'division', 'lat', 'long')
    list_filter = ('division',)
    search_fields = ('name', 'bn_name')

@admin.register(SubDistrict)
class SubDistrictAdmin(admin.ModelAdmin):
    list_display = ('name', 'district', 'bn_name')
    list_filter = ('district__division', 'district')
    search_fields = ('name', 'bn_name')


# --- User Admin Integration ---

class ProfileInline(admin.StackedInline):
    model = Customer
    can_delete = False
    verbose_name_plural = 'Customer Profile'
    verbose_name_plural = 'Customer Profile'
    fk_name = 'user'

class EmailAddressInline(admin.StackedInline):
    model = EmailAddress
    extra = 0
    can_delete = False
    verbose_name_plural = 'Email Addresses'

# Define a new User admin


class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline, EmailAddressInline)


# Re-register UserAdmin
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, UserAdmin)
