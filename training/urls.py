from rest_framework.routers import DefaultRouter

from training.views import (
    ExerciseViewSet,
    ProgramViewSet,
    SessionSetViewSet,
    SessionViewSet,
)

router = DefaultRouter()
router.register(r'exercises', ExerciseViewSet, basename='exercise')
router.register(r'programs', ProgramViewSet, basename='program')
router.register(r'sessions', SessionViewSet, basename='session')
router.register(r'session-sets', SessionSetViewSet, basename='sessionset')

urlpatterns = router.urls
