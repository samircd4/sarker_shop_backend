from rest_framework import viewsets, filters, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Order, Cart, Checkout, CartItem, OrderStatus
from .serializers import OrderSerializer, CartSerializer, CheckoutSerializer, CartItemSerializer

class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['order_status__status_code', 'payment_info__is_paid']
    ordering_fields = ['created_at', 'total_amount']

    def get_queryset(self):
        if self.request.user.is_staff:
            return Order.objects.all()
        if hasattr(self.request.user, 'customer'):
            return Order.objects.filter(customer=self.request.user.customer)
        return Order.objects.none()

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
        return CartItem.objects.filter(cart__user=self.request.user)

    def list(self, request, *args, **kwargs):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart)
        return Response(serializer.data)

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

    @action(detail=False, methods=['delete'])
    def clear(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart.items.all().delete()
        return Response({'status': 'cart cleared'}, status=status.HTTP_204_NO_CONTENT)

class CheckoutViewSet(viewsets.ModelViewSet):
    serializer_class = CheckoutSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Checkout.objects.filter(cart__user=self.request.user)
