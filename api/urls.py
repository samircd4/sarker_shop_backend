from django.urls import path, include
from .views import api_root
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('', api_root, name='api-root'),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', login_required(SpectacularSwaggerView.as_view(url_name='schema',
         template_name='swagger_ui.html')), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    path('', include('accounts.urls')),
    path('', include('orders.urls')),
    path('', include('products.urls')),
    path('', include('reviews.urls')),
]
