from rest_framework import viewsets, mixins, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import ContactMessage, NewsletterSubscription
from .serializers import ContactMessageSerializer, NewsletterSubscriptionSerializer

class ContactMessageViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = ContactMessage.objects.all()
    serializer_class = ContactMessageSerializer
    permission_classes = [AllowAny]

class NewsletterSubscriptionViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = NewsletterSubscription.objects.all()
    serializer_class = NewsletterSubscriptionSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        # We handle existing emails by just returning success or a specific message
        email = request.data.get('email')
        if NewsletterSubscription.objects.filter(email=email).exists():
            return Response(
                {"detail": "You are already subscribed to our newsletter."},
                status=status.HTTP_200_OK
            )
        return super().create(request, *args, **kwargs)
