from rest_framework import viewsets, filters
from rest_framework.permissions import BasePermission, SAFE_METHODS
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import Review, Question
from .serializers import ReviewSerializer, QuestionSerializer


class IsReviewOwnerOrReadOnly(BasePermission):
    """
    Review owners can edit/delete their reviews.
    Admins can edit/delete all.
    Everyone can read.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        # obj.customer.user should be compared to request.user
        return obj.customer.user == request.user or request.user.is_staff


@extend_schema_view(
    list=extend_schema(tags=['Product Q&A']),
    create=extend_schema(tags=['Product Q&A']),
    retrieve=extend_schema(tags=['Product Q&A']),
    update=extend_schema(tags=['Product Q&A']),
    partial_update=extend_schema(tags=['Product Q&A']),
    destroy=extend_schema(tags=['Product Q&A']),
)
class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all().order_by('-created_at')
    serializer_class = QuestionSerializer
    permission_classes = [IsReviewOwnerOrReadOnly]  # Reuse same logic for now

    filter_backends = [DjangoFilterBackend,
                       filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ['product']
    search_fields = ['question', 'answer']
    ordering_fields = ['created_at']

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user.customer)

@extend_schema(tags=['Reviews'])
class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsReviewOwnerOrReadOnly]

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['product', 'rating']
    ordering_fields = ['created_at', 'rating']

    def perform_create(self, serializer):
        serializer.save(customer=self.request.user.customer)
