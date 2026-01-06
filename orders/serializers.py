from rest_framework import serializers
from django.db import transaction
from accounts.serializers import AddressSerializer
from products.models import Product, ProductVariant
from accounts.models import Address
from .models import Order, OrderItem, Cart, CartItem, Checkout, PaymentInfo, OrderStatus

from drf_spectacular.utils import extend_schema_field


class OrderProductSerializer(serializers.ModelSerializer):
    """
    Used inside Orders to show minimal product info.
    """
    price = serializers.SerializerMethodField()
    wholesale_price = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'wholesale_price', 'image', 'slug']

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            url = obj.image.url
            if request:
                return request.build_absolute_uri(url)
            return url
        return None

    def get_price(self, obj):
        discount = getattr(obj, 'display_discount_price', None)
        if discount:
            return discount
        return getattr(obj, 'display_price', None)

    def get_wholesale_price(self, obj):
        return getattr(obj, 'display_wholesale_price', None)


class OrderVariantSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductVariant
        fields = [
            'id', 'sku', 'price', 'wholesale_price', 'discount_price',
            'stock_quantity', 'ram', 'storage', 'color'
        ]


class OrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatus
        fields = ['status_code', 'display_name']


class PaymentInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentInfo
        fields = ['transaction_id', 'is_paid',
                  'payment_method', 'payment_date']


class OrderItemSerializer(serializers.ModelSerializer):
    product = OrderProductSerializer(read_only=True)
    variant = OrderVariantSerializer(read_only=True)
    ram = serializers.IntegerField(source='variant.ram', read_only=True)
    storage = serializers.IntegerField(
        source='variant.storage', read_only=True)
    color = serializers.CharField(source='variant.color', read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True, required=False
    )
    variant_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.all(), source='variant', write_only=True, required=False
    )
    subtotal = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'variant', 'ram', 'storage', 'color', 'product_id', 'variant_id',
                  'quantity', 'price', 'subtotal']
        read_only_fields = ['price', 'subtotal']

    def validate(self, data):
        # Require either product or variant
        if not data.get('product') and not data.get('variant'):
            raise serializers.ValidationError(
                "Provide product_id or variant_id.")
        return data


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    # Address Handling
    address = AddressSerializer(read_only=True)  # Legacy object display
    address_id = serializers.PrimaryKeyRelatedField(
        queryset=Address.objects.all(), source='address', write_only=True, required=False, allow_null=True
    )

    # Guest / Snapshot Fields
    email = serializers.EmailField(required=False)
    full_name = serializers.CharField(required=False)
    phone = serializers.CharField(required=False)
    shipping_address = serializers.CharField(required=False)
    division = serializers.CharField(required=False)
    district = serializers.CharField(required=False)
    sub_district = serializers.CharField(required=False)

    # Flattened fields for backward compatibility / ease of use
    status = serializers.CharField(
        source='order_status.display_name', read_only=True)
    payment = PaymentInfoSerializer(source='payment_info', read_only=True)

    items_input = serializers.ListField(
        child=serializers.DictField(), write_only=True, required=False
    )

    class Meta:
        model = Order
        fields = [
            'id',
            'status',       # Read-only string
            'total_amount',
            'payment',      # Read-only nested object
            'created_at',
            'address',      # Legacy object (Read)
            'address_id',   # Legacy ID (Write - Optional)

            # Guest Fields
            'email', 'full_name', 'phone',
            'shipping_address', 'division', 'district', 'sub_district',

            'items',        # Full objects (Read)
            'items_input'   # List of dicts (Write)
        ]
        read_only_fields = ['total_amount', 'status', 'payment', 'created_at']

    def validate(self, data):
        request = self.context['request']
        user = request.user

        # Items can come from items_input or from the user's/session cart
        if not data.get('items_input'):
            # Try to resolve cart
            cart = None
            if user.is_authenticated:
                cart = Cart.objects.filter(user=user).first()
            else:
                # Ensure session exists
                if not request.session.session_key:
                    request.session.create()
                cart = Cart.objects.filter(
                    session_key=request.session.session_key).first()
            if not cart or cart.items.count() == 0:
                raise serializers.ValidationError(
                    "Order must contain items (cart is empty).")

        # Guest must provide minimal identity and shipping
        if not user.is_authenticated:
            required_fields = ['email', 'full_name', 'phone',
                               'shipping_address', 'division', 'district']
            missing = [f for f in required_fields if not data.get(f)]
            if missing:
                raise serializers.ValidationError(
                    f"Guest checkout requires: {', '.join(missing)}")
        return data

    def create(self, validated_data):
        request = self.context['request']
        items_data = validated_data.pop('items_input', None)
        user = request.user

        customer = None
        is_wholesaler = False

        if user.is_authenticated:
            customer = user.customer
            is_wholesaler = customer.is_wholesaler

        # Handle Address Logic
        # If address_id is provided, copy data from it to snapshot fields
        address_obj = validated_data.get('address')
        if address_obj:
            validated_data['full_name'] = validated_data.get(
                'full_name') or address_obj.full_name
            validated_data['phone'] = validated_data.get(
                'phone') or address_obj.phone
            validated_data['shipping_address'] = validated_data.get(
                'shipping_address') or address_obj.address
            validated_data['division'] = validated_data.get(
                'division') or address_obj.division
            validated_data['district'] = validated_data.get(
                'district') or address_obj.district
            validated_data['sub_district'] = validated_data.get(
                'sub_district') or address_obj.sub_district
            # If authenticated, email might default to user email
            if not validated_data.get('email') and customer:
                validated_data['email'] = customer.email

        with transaction.atomic():
            # Create Default Status if needed (or fetch 'pending')
            pending_status, _ = OrderStatus.objects.get_or_create(
                status_code='pending',
                defaults={'display_name': 'Pending'}
            )

            # Create Payment Info placeholder
            payment_info = PaymentInfo.objects.create()

            # Create Order
            order = Order.objects.create(
                customer=customer,
                order_status=pending_status,
                payment_info=payment_info,
                **validated_data
            )

            # Source items: provided items_input or current cart items
            if items_data:
                source_items = items_data
                is_cart = False
            else:
                # Build from cart
                is_cart = True
                cart = None
                if user.is_authenticated:
                    cart = Cart.objects.filter(user=user).first()
                else:
                    if not request.session.session_key:
                        request.session.create()
                    cart = Cart.objects.filter(
                        session_key=request.session.session_key).first()
                source_items = [
                    {
                        'product_id': ci.product_id,
                        'variant_id': ci.variant_id,
                        'quantity': ci.quantity
                    }
                    for ci in cart.items.all()
                ]

            for item in source_items:
                quantity = item.get('quantity', 1)
                variant_id = item.get('variant_id')
                product_id = item.get('product_id')

                if variant_id:
                    variant = ProductVariant.objects.get(id=variant_id)
                    product = variant.product
                    v_wholesale = getattr(variant, 'wholesale_price', None)
                    v_discount = getattr(variant, 'discount_price', None)
                    v_price = getattr(variant, 'price', None)

                    if is_wholesaler and v_wholesale and v_wholesale > 0:
                        final_price = v_wholesale
                    elif v_discount and v_discount > 0:
                        final_price = v_discount
                    else:
                        final_price = v_price

                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        variant=variant,
                        quantity=quantity,
                        price=final_price
                    )
                else:
                    product = Product.objects.get(id=product_id)
                    # If product has variants but none specified, pick a default active variant (min price)
                    default_variant = product.variants.filter(
                        is_active=True).order_by('price').first()
                    if default_variant:
                        v_wholesale = getattr(
                            default_variant, 'wholesale_price', None)
                        v_discount = getattr(
                            default_variant, 'discount_price', None)
                        v_price = getattr(default_variant, 'price', None)

                        if is_wholesaler and v_wholesale and v_wholesale > 0:
                            final_price = v_wholesale
                        elif v_discount and v_discount > 0:
                            final_price = v_discount
                        else:
                            final_price = v_price

                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            variant=default_variant,
                            quantity=quantity,
                            price=final_price
                        )
                    else:
                        wholesale = getattr(
                            product, 'display_wholesale_price', None)
                        discount = getattr(
                            product, 'display_discount_price', None)
                        base_price = getattr(product, 'display_price', None)

                        if is_wholesaler and wholesale and wholesale > 0:
                            final_price = wholesale
                        elif discount and discount > 0:
                            final_price = discount
                        else:
                            final_price = base_price

                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            quantity=quantity,
                            price=final_price
                        )

            # Optionally clear cart after order creation
            if 'is_cart' in locals() and is_cart:
                try:
                    cart.items.all().delete()
                except Exception:
                    pass

            # Assuming update_total_amount exists on Order model
            if hasattr(order, 'update_total_amount'):
                order.update_total_amount()
            else:
                # Fallback calculation if method missing
                total = sum(
                    item.price * item.quantity for item in order.items.all())
                order.total_amount = total
                order.save()

        return order


class CartItemSerializer(serializers.ModelSerializer):
    product = OrderProductSerializer(read_only=True)
    variant = OrderVariantSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True, required=False
    )
    variant_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductVariant.objects.all(), source='variant', write_only=True, required=False
    )

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'variant',
                  'product_id', 'variant_id', 'quantity']

    def validate(self, data):
        # Require either product or variant
        if not data.get('product') and not data.get('variant'):
            raise serializers.ValidationError(
                "Provide product_id or variant_id.")
        return data


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'items', 'created_at']


class CheckoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Checkout
        fields = '__all__'
