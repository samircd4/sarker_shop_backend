from rest_framework import serializers
from django.db import transaction
import json

from .models import (
    Category, Brand, Product, ProductImage, ProductSpecification,
    Address, Order, OrderItem, Review, Customer
)


###########################################################################


# --- Helper Serializers ---
class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image']

class ProductSpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSpecification
        fields = ['key', 'value']

class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ['id', 'name', 'slug', 'logo']

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'logo']

# --- Main Product Serializer ---
class ProductSerializer(serializers.ModelSerializer):
    # Read-only nested fields (for display)
    brand = BrandSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    gallery_images = ProductImageSerializer(many=True, read_only=True)
    specifications = ProductSpecificationSerializer(many=True, read_only=True)

    # Write-only fields (for input)
    brand_id = serializers.PrimaryKeyRelatedField(
        queryset=Brand.objects.all(), source='brand', write_only=True
    )
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), source='category', write_only=True
    )
    
    # Special field to accept multiple images (Write Only)
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(allow_empty_file=False, use_url=False),
        write_only=True,
        required=False
    )
    
    # Special field to accept specs as a JSON string (easier for React/Postman)
    specs_input = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = Product
        fields = [
            'id', 'product_id', 'sku', 'name', 'slug', 
            'description', 'short_description', 
            'price', 'wholesale_price', 'discount_price', 
            'brand', 'brand_id', 
            'category', 'category_id', 
            'image',            # Main cover image
            'uploaded_images',  # Gallery images (Input)
            'gallery_images',   # Gallery images (Output)
            'specs_input',      # Specs (Input)
            'specifications',   # Specs (Output)
            'rating', 'reviews_count', 'stock_quantity', 
            'is_featured', 'is_active', 'created_at', 'updated_at',
        ]

    def create(self, validated_data):
        # 1. Pop (remove) the nested data that isn't part of the Product model
        uploaded_images = validated_data.pop('uploaded_images', [])
        specs_input = validated_data.pop('specs_input', [])
        
        # 2. Create the Main Product
        product = Product.objects.create(**validated_data)

        # 3. Create Gallery Images
        for image in uploaded_images:
            ProductImage.objects.create(product=product, image=image)

        # 4. Create Specifications
        # Note: If sending from Postman form-data, it might come as a string, so we parse it.
        if specs_input:
            if isinstance(specs_input, str):
                try:
                    specs_input = json.loads(specs_input)
                except ValueError:
                    specs_input = []
            
            for spec in specs_input:
                ProductSpecification.objects.create(
                    product=product, 
                    key=spec.get('key'), 
                    value=spec.get('value')
                )

        return product


# --- 0. HELPER SERIALIZERS (To avoid circular imports) ---

class SimpleProductSerializer(serializers.ModelSerializer):
    """
    Used inside Orders and Reviews to show minimal product info.
    Prevents loading the full product details (specs, all images) unnecessarily.
    """
    image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'wholesale_price', 'image', 'slug']

    def get_image(self, obj):
        # Return full URL of the main image
        if obj.image:
            return obj.image.url
        return None


# --- 1. CUSTOMER & PROFILE ---

class CustomerSerializer(serializers.ModelSerializer):
    """
    Read/Write customer details.
    """
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Customer
        fields = [
            'id', 'user', 'username', 'name', 
            'email', 'phone_number', 'customer_type', 
            'is_wholesaler', 'created_at'
        ]
        read_only_fields = ['user', 'customer_type', 'created_at']


# --- 2. ADDRESS BOOK ---

class AddressSerializer(serializers.ModelSerializer):
    """
    Matches the UI screenshot exactly.
    """
    class Meta:
        model = Address
        fields = [
            'id', 
            'full_name', 'phone',           # Contact
            'address',                      # House/Road
            'division', 'district', 'sub_district', # Location
            'address_type', 'is_default'    # Meta
        ]

    def create(self, validated_data):
        # Automatically assign the logged-in user's customer profile
        user = self.context['request'].user
        validated_data['customer'] = user.customer
        return super().create(validated_data)


# --- 3. REVIEWS ---

class ReviewSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'product', 'rating', 'comment', 'customer_name', 'created_at']
        read_only_fields = ['customer']

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['customer'] = user.customer
        return super().create(validated_data)


# --- 4. ORDER SYSTEM (The Complex Part) ---

class OrderItemSerializer(serializers.ModelSerializer):
    """
    For displaying items inside an order.
    """
    product = SimpleProductSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(), source='product', write_only=True
    )

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_id', 'quantity', 'price', 'subtotal']
        read_only_fields = ['price', 'subtotal']


class OrderSerializer(serializers.ModelSerializer):
    """
    Handles Creating and Viewing Orders.
    """
    # Nested serializers for reading
    items = OrderItemSerializer(many=True, read_only=True)
    address = AddressSerializer(read_only=True)
    
    # Write-only fields for creating an order
    address_id = serializers.PrimaryKeyRelatedField(
        queryset=Address.objects.all(), source='address', write_only=True
    )
    # Accepts a list of items: [{"product_id": 1, "quantity": 2}, ...]
    items_input = serializers.ListField(
        child=serializers.DictField(), write_only=True
    )

    class Meta:
        model = Order
        fields = [
            'id', 
            'order_status', 
            'total_amount', 
            'is_paid', 
            'transaction_id', 
            'created_at', 
            'address',      # Full object (Read)
            'address_id',   # ID only (Write)
            'items',        # Full objects (Read)
            'items_input'   # List of dicts (Write)
        ]
        read_only_fields = ['total_amount', 'order_status', 'is_paid', 'transaction_id']

    def create(self, validated_data):
        """
        Custom create method to handle:
        1. Order Creation
        2. OrderItems Creation
        3. Wholesale vs Retail Price Logic
        """
        items_data = validated_data.pop('items_input')
        user = self.context['request'].user
        customer = user.customer
        
        # 1. Start Atomic Transaction (Safety first!)
        with transaction.atomic():
            # Create the Order
            order = Order.objects.create(customer=customer, **validated_data)
            
            # 2. Loop through items and create OrderItems
            for item in items_data:
                product_id = item.get('product_id')
                quantity = item.get('quantity', 1)
                
                # Fetch product to check price
                product = Product.objects.get(id=product_id)
                
                # --- WHOLESALE LOGIC ---
                # If customer is wholesale, use wholesale_price, else use price
                if customer.is_wholesaler and product.wholesale_price > 0:
                    final_price = product.wholesale_price
                else:
                    final_price = product.price
                
                # Create OrderItem
                # Note: We manually set price here to ensure wholesale logic applies
                # overriding the default model save() logic if needed
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=final_price
                )
            
            # 3. Trigger the total update (Model method)
            order.update_total_amount()
            
        return order