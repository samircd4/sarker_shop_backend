from rest_framework import serializers
from django.db import transaction
from accounts.serializers import AddressSerializer
from products.models import Product
from accounts.models import Address
from .models import Order, OrderItem, Cart, CartItem, Checkout, PaymentInfo, OrderStatus

class SimpleProductSerializer(serializers.ModelSerializer):
    """
    Used inside Orders to show minimal product info.
    """
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'wholesale_price', 'image', 'slug']

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
        fields = ['transaction_id', 'is_paid', 'payment_method', 'payment_date']

class OrderItemSerializer(serializers.ModelSerializer):
    product = SimpleProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True
    )

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_id', 'quantity', 'price', 'subtotal']
        read_only_fields = ['price', 'subtotal']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    address = AddressSerializer(read_only=True)
    
    # Flattened fields for backward compatibility / ease of use
    status = serializers.CharField(source='order_status.display_name', read_only=True)
    payment = PaymentInfoSerializer(source='payment_info', read_only=True)

    address_id = serializers.PrimaryKeyRelatedField(
        queryset=Address.objects.all(), source='address', write_only=True
    )
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
            'address',      # Full object (Read)
            'address_id',   # ID only (Write)
            'items',        # Full objects (Read)
            'items_input'   # List of dicts (Write)
        ]
        read_only_fields = ['total_amount', 'status', 'payment', 'created_at']

    def create(self, validated_data):
        items_data = validated_data.pop('items_input')
        user = self.context['request'].user
        customer = user.customer

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

                if customer.is_wholesaler and product.wholesale_price > 0:
                    final_price = product.wholesale_price
                else:
                    final_price = product.price

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=final_price
                )

            order.update_total_amount()

        return order

class CartItemSerializer(serializers.ModelSerializer):
    product = SimpleProductSerializer(read_only=True)
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
