from django.contrib import admin
from django.utils.html import format_html
from django.conf import settings
from django.forms.models import BaseInlineFormSet
from .models import Order, OrderItem, OrderStatus, PaymentInfo, Cart, Checkout, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 1


class OrderItemInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        for form in self.forms:
            if not form.cleaned_data.get('price') and form.cleaned_data.get('product'):
                form.cleaned_data['price'] = form.cleaned_data['product'].price


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    formset = OrderItemInlineFormSet
    extra = 1


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    readonly_fields = ('total_amount', 'invoice_link')

    list_display = (
        'id',
        'customer',
        'total_amount',
        'order_status',
        'created_at',
        'phone',
        'payment_info',
        'invoice_link',
    )

    list_filter = ('order_status', 'created_at')
    search_fields = ('customer__name', 'customer__email', 'id', 'phone')
    inlines = [OrderItemInline]

    def invoice_link(self, obj):
        if not obj.pk:
            return "-"
        url = f"/api/orders/{obj.id}/invoice/"
        return format_html('<a href="{}" target="_blank">📄 Download Invoice</a>', url)

    invoice_link.short_description = "Invoice"


@admin.register(OrderStatus)
class OrderStatusAdmin(admin.ModelAdmin):
    list_display = ('status_code', 'display_name')
    search_fields = ('status_code', 'display_name')


@admin.register(PaymentInfo)
class PaymentInfoAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'is_paid',
                    'payment_method', 'created_at')
    list_filter = ('is_paid', 'payment_method')
    search_fields = ('transaction_id',)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session_key', 'created_at', 'updated_at')
    search_fields = ('user__username', 'session_key')
    inlines = [CartItemInline]


@admin.register(Checkout)
class CheckoutAdmin(admin.ModelAdmin):
    list_display = ('id', 'cart', 'email', 'created_at')
    search_fields = ('email', 'cart__id')
