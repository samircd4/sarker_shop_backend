from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.reverse import reverse
from drf_spectacular.utils import extend_schema


@extend_schema(exclude=True)
@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request, format=None):
    return Response({
        'documentation': reverse('swagger-ui', request=request, format=format),
        'visual doc': reverse('redoc', request=request, format=format),
        'auth': {
            'register': reverse('auth_register', request=request, format=format),
            'login': reverse('token_obtain_pair', request=request, format=format),
            'refresh': reverse('token_refresh', request=request, format=format),
            'logout': reverse('auth_logout', request=request, format=format),
            'change_password': reverse('change_password', request=request, format=format),
            'forgot_password': reverse('forgot_password', request=request, format=format),
            'reset_password': reverse('reset_password', request=request, format=format),
        },
        'accounts': {
            'customers': reverse('customer-list', request=request, format=format),
            'addresses': reverse('address-list', request=request, format=format),
        },
        'catalog': {
            'products': reverse('product-list', request=request, format=format),
            'categories': reverse('category-list', request=request, format=format),
            'brands': reverse('brand-list', request=request, format=format),
        },
        'reviews': {
            'reviews': reverse('review-list', request=request, format=format),
        },
        'orders': {
            'orders': reverse('order-list', request=request, format=format),
            'cart': reverse('cart-list', request=request, format=format),
            'checkout': reverse('checkout-list', request=request, format=format),
        },
    })
