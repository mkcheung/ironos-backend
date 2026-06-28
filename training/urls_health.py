from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views_health

router = DefaultRouter()
router.register(r'bodyweight', views_health.BodyweightViewSet, basename='bodyweight')
router.register(r'body-composition', views_health.BodyCompositionViewSet, basename='bodycomposition')
router.register(r'cardio', views_health.CardioViewSet, basename='cardio')
router.register(r'heart-rate', views_health.HeartRateViewSet, basename='heartrate')
router.register(r'nutrition/targets', views_health.NutritionTargetsViewSet, basename='nutritiontarget')
router.register(r'goals', views_health.GoalViewSet, basename='goal')
router.register(r'reports', views_health.ReportViewSet, basename='report')

urlpatterns = router.urls + [
    path('dashboard/summary/', views_health.DashboardSummaryView.as_view(), name='dashboard-summary'),
    path('tasks/<str:task_id>/', views_health.TaskStatusView.as_view(), name='task-status'),
]
