from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ContactMessageViewSet, NewsletterSubscriptionViewSet

router = DefaultRouter()
router.register(r'contact', ContactMessageViewSet, basename='contact')
router.register(r'subscribe', NewsletterSubscriptionViewSet, basename='subscribe')

urlpatterns = [
    path('', include(router.urls)),
]
