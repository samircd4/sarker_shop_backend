from django.contrib import admin
from django.utils.html import format_html
# from django.conf import settings
from django.forms.models import BaseInlineFormSet
from django import forms
from django.http import JsonResponse
from django.urls import path
from .models import Order, OrderItem, OrderStatus, PaymentInfo, Cart, Checkout, CartItem
from products.models import ProductVariant


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 1
    fields = ('product', 'variant', 'quantity')

    class Form(forms.ModelForm):
        class Meta:
            model = CartItem
            fields = ('product', 'variant', 'quantity')

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Use bound data if available, else instance
            product_id = self.data.get(self.add_prefix('product')) or getattr(
                self.instance, 'product_id', None)
            if product_id:
                self.fields['variant'].queryset = ProductVariant.objects.filter(
                    product_id=product_id)
            else:
                self.fields['variant'].queryset = ProductVariant.objects.none()
            # Friendly labels: sku | Color | ram/storage

            def _label(v):
                parts = [v.sku]
                if v.color:
                    parts.append(v.color)
                rs = []
                if v.ram:
                    rs.append(f"{v.ram}GB")
                if v.storage:
                    rs.append(f"{v.storage}GB")
                if rs:
                    parts.append("/".join(rs))
                return " | ".join(parts)
            self.fields['variant'].label_from_instance = _label
    form = Form


class OrderItemInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        for form in self.forms:
            if not form.cleaned_data.get('price'):
                variant = form.cleaned_data.get('variant')
                product = form.cleaned_data.get('product')
                if variant:
                    form.cleaned_data['price'] = variant.price
                elif product:
                    form.cleaned_data['price'] = product.price


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    formset = OrderItemInlineFormSet
    extra = 1
    fields = ('product', 'variant', 'quantity', 'price')

    class Form(forms.ModelForm):
        class Meta:
            model = OrderItem
            fields = ('product', 'variant', 'quantity', 'price')

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            product_id = self.data.get(self.add_prefix('product')) or getattr(
                self.instance, 'product_id', None)
            if product_id:
                self.fields['variant'].queryset = ProductVariant.objects.filter(
                    product_id=product_id)
            else:
                self.fields['variant'].queryset = ProductVariant.objects.none()

            def _label(v):
                parts = [v.sku]
                if v.color:
                    parts.append(v.color)
                rs = []
                if v.ram:
                    rs.append(f"{v.ram}GB")
                if v.storage:
                    rs.append(f"{v.storage}GB")
                if rs:
                    parts.append("/".join(rs))
                return " | ".join(parts)
            self.fields['variant'].label_from_instance = _label
    form = Form

    class Media:
        js = ('orders/admin_inline.js',)


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

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('variants/', self.admin_site.admin_view(self.variant_options),
                 name='order_variant_options'),
        ]
        return custom + urls

    def variant_options(self, request):
        product_id = request.GET.get('product_id')
        if not product_id:
            return JsonResponse({'variants': []})
        qs = ProductVariant.objects.filter(
            product_id=product_id, is_active=True).order_by('price')

        def _label(v):
            parts = [v.sku]
            if v.color:
                parts.append(v.color)
            rs = []
            if v.ram:
                rs.append(f"{v.ram}GB")
            if v.storage:
                rs.append(f"{v.storage}GB")
            if rs:
                parts.append("/".join(rs))
            return " | ".join(parts)
        data = [{'id': v.id, 'label': _label(
            v), 'price': str(v.price)} for v in qs]
        return JsonResponse({'variants': data})


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

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('variants/', self.admin_site.admin_view(self.variant_options),
                 name='cart_variant_options'),
        ]
        return custom + urls

    def variant_options(self, request):
        product_id = request.GET.get('product_id')
        if not product_id:
            return JsonResponse({'variants': []})
        qs = ProductVariant.objects.filter(
            product_id=product_id, is_active=True).order_by('price')

        def _label(v):
            parts = [v.sku]
            if v.color:
                parts.append(v.color)
            rs = []
            if v.ram:
                rs.append(f"{v.ram}GB")
            if v.storage:
                rs.append(f"{v.storage}GB")
            if rs:
                parts.append("/".join(rs))
            return " | ".join(parts)
        data = [{'id': v.id, 'label': _label(
            v), 'price': str(v.price)} for v in qs]
        return JsonResponse({'variants': data})


@admin.register(Checkout)
class CheckoutAdmin(admin.ModelAdmin):
    list_display = ('id', 'cart', 'email', 'created_at')
    search_fields = ('email', 'cart__id')
