from rest_framework import serializers
from django.db import transaction
from accounts.serializers import AddressSerializer
from products.models import Product
from accounts.models import Address
from .models import Order, OrderItem, Cart, CartItem, Checkout, PaymentInfo, OrderStatus

from drf_spectacular.utils import extend_schema_field


class OrderProductSerializer(serializers.ModelSerializer):
    """
    Used inside Orders to show minimal product info.
    """
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'wholesale_price', 'image', 'slug']

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_image(self, obj):
        if obj.image:
            return obj.image.url
        return None


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
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True
    )
    subtotal = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_id',
                  'quantity', 'price', 'subtotal']
        read_only_fields = ['price', 'subtotal']


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
        child=serializers.DictField(), write_only=True
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
        user = self.context['request'].user

        # 1. Validate Items
        if not data.get('items_input'):
            raise serializers.ValidationError("Order must contain items.")

        # 2. Validate Address Info
        # If user is anonymous, they MUST provide full address details
        if not user.is_authenticated:
            required_fields = ['email', 'full_name', 'phone',
                               'shipping_address', 'division', 'district']
            missing = [f for f in required_fields if not data.get(f)]
            if missing:
                raise serializers.ValidationError(
                    f"Guest checkout requires: {', '.join(missing)}")

        # If authenticated, they can use address_id OR provide new details
        # (Logic handled in create)

        return data

    def create(self, validated_data):
        items_data = validated_data.pop('items_input')
        user = self.context['request'].user

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

            for item in items_data:
                product_id = item.get('product_id')
                quantity = item.get('quantity', 1)
                product = Product.objects.get(id=product_id)

                if is_wholesaler and product.wholesale_price > 0:
                    final_price = product.wholesale_price
                else:
                    final_price = product.price

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=final_price
                )

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
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True
    )

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity']


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'items', 'created_at']


class CheckoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Checkout
        fields = '__all__'
