from rest_framework.routers import DefaultRouter
from .views import EvaluationViewSet, QuestionViewSet

evaluations_router = DefaultRouter()
evaluations_router.register('', EvaluationViewSet, basename='evaluations')

questions_router = DefaultRouter()
questions_router.register('', QuestionViewSet, basename='questions')
