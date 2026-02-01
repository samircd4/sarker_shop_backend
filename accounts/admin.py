from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Customer, Address, Division, District, SubDistrict

# --- 1. CUSTOMER ADMIN ---


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    # Now you can see Email and Phone directly in the list
    list_display = ('name', 'email', 'phone_number', 'customer_type', 'user')
    list_filter = ('customer_type', 'created_at')
    search_fields = ('name', 'email', 'phone_number', 'user__username')

    # You can also edit the user link if needed, but usually read-only
    raw_id_fields = ('user',)


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
    fk_name = 'user'

# Define a new User admin


class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)


# Re-register UserAdmin
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, UserAdmin)
