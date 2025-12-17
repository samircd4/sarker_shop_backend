from django.urls import path, include
from .views import api_root

urlpatterns = [
    path('', api_root, name='api-root'),
    path('', include('accounts.urls')),
    path('', include('orders.urls')),
    path('', include('products.urls')),
    path('', include('reviews.urls')),
]
