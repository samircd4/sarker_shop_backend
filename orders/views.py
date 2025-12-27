from rest_framework import viewsets, filters, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from .models import Order, Cart, Checkout, CartItem, OrderStatus
from .serializers import OrderSerializer, CartSerializer, CheckoutSerializer, CartItemSerializer


@extend_schema(tags=['Orders'])
class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    # permission_classes = [permissions.IsAuthenticated] # Overridden by get_permissions
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['order_status__status_code', 'payment_info__is_paid']
    ordering_fields = ['created_at', 'total_amount']

    @extend_schema(
        summary="Create Order",
        description="""
        Create a new order.
        
        **For Authenticated Users:**
        - Can use existing saved address via `address_id` OR provide new address details.
        
        **For Guest Users:**
        - Must provide all address fields: `email`, `full_name`, `phone`, `shipping_address`, `division`, `district`.
        """,
        responses={201: OrderSerializer}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Order.objects.none()

        # Check if user is authenticated before accessing customer
        if not self.request.user.is_authenticated:
            return Order.objects.none()

        if self.request.user.is_staff:
            return Order.objects.all()

        if hasattr(self.request.user, 'customer'):
            return Order.objects.filter(customer=self.request.user.customer)

        return Order.objects.none()

    @extend_schema(
        summary="Update Order Status",
        request=None,
        parameters=[
            OpenApiParameter("status", OpenApiTypes.STR,
                             description="Status Code", required=True)
        ],
        responses={200: OpenApiTypes.OBJECT}
    )
    @action(detail=True, methods=['patch'])
    def status(self, request, pk=None):
        order = self.get_object()
        status_code = request.data.get('status')
        if not status_code:
            return Response({'error': 'status is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_status = OrderStatus.objects.get(status_code=status_code)
            order.order_status = new_status
            order.save()
            return Response({'status': 'updated', 'new_status': new_status.display_name})
        except OrderStatus.DoesNotExist:
            return Response({'error': 'Invalid status code'}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(tags=['Cart'])
class CartViewSet(viewsets.ModelViewSet):
    """
    Manage Shopping Cart.
    Routes:
    GET /api/cart/ -> Returns the User's Cart (with items)
    POST /api/cart/ -> Add Item to Cart
    PUT /api/cart/{id}/ -> Update Item Quantity
    DELETE /api/cart/{id}/ -> Remove Item
    DELETE /api/cart/clear/ -> Clear Cart
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CartItemSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return CartItem.objects.none()
        return CartItem.objects.filter(cart__user=self.request.user)

    @extend_schema(
        summary="Get Cart",
        description="Returns the User's Cart (with items)",
        responses={200: CartSerializer}
    )
    def list(self, request, *args, **kwargs):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)

    @extend_schema(
        summary="Add Item to Cart",
        description="Add an item to the cart or update quantity if it exists.",
        responses={201: CartItemSerializer}
    )
    def create(self, request, *args, **kwargs):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product = serializer.validated_data['product']
        quantity = serializer.validated_data['quantity']

        # Check if item exists
        item, created = CartItem.objects.get_or_create(
            cart=cart, product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            item.quantity += quantity
            item.save()

        # Return the updated item
        return Response(self.get_serializer(item).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Clear Cart",
        description="Remove all items from the cart.",
        responses={204: None}
    )
    @action(detail=False, methods=['delete'])
    def clear(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart.items.all().delete()
        return Response({'status': 'cart cleared'}, status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=['Cart Items'])
class CartItemViewSet(viewsets.ModelViewSet):
    """
    Manage Cart Items:
    - GET /api/cart-items/ : List all items in cart
    - POST /api/cart-items/ : Add item to cart
    - GET /api/cart-items/{id}/ : Retrieve specific item
    - PATCH /api/cart-items/{id}/ : Update quantity
    - DELETE /api/cart-items/{id}/ : Remove item from cart
    """
    serializer_class = CartItemSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return CartItem.objects.none()
        return CartItem.objects.filter(cart__user=self.request.user)

    def perform_create(self, serializer):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        product = serializer.validated_data['product']
        quantity = serializer.validated_data.get('quantity', 1)

        # Check if item exists
        item, created = CartItem.objects.get_or_create(
            cart=cart, product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            item.quantity += quantity
            item.save()
            # We need to update the serializer instance to point to the updated item
            # But perform_create doesn't return response.
            # We can't easily swap the instance here for the response.
            # However, ModelViewSet calls serializer.save() which calls perform_create.
            # We can override create() instead.
            pass

    def create(self, request, *args, **kwargs):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        product = serializer.validated_data['product']
        quantity = serializer.validated_data['quantity']

        # Check if item exists
        item, created = CartItem.objects.get_or_create(
            cart=cart, product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            item.quantity += quantity
            item.save()

        # Return the updated/created item
        return Response(self.get_serializer(item).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Checkout'])
class CheckoutViewSet(viewsets.ModelViewSet):
    serializer_class = CheckoutSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Checkout.objects.none()
        return Checkout.objects.filter(cart__user=self.request.user)
