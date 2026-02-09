from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReviewViewSet, QuestionViewSet

router = DefaultRouter()
router.register(r'reviews', ReviewViewSet)
router.register(r'questions', QuestionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
