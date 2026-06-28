from datetime import date, timedelta

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from training.models import (
    BodyweightEntry,
    BodyCompositionEntry,
    HeartRateEntry,
    CardioSession,
    NutritionTarget,
    WeeklyReport,
    Goal,
)
from training.serializers_health import (
    BodyweightEntrySerializer,
    BodyCompositionEntrySerializer,
    HeartRateEntrySerializer,
    CardioSessionSerializer,
    NutritionTargetSerializer,
    WeeklyReportSerializer,
    GoalSerializer,
)
from training.analytics import (
    bodyweight_trend,
    zone_minutes_trend,
    goal_progress,
    adherence,
    weekly_volume_by_muscle,
    estimate_1rm,
)


class BodyweightViewSet(viewsets.ModelViewSet):
    serializer_class = BodyweightEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BodyweightEntry.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'], url_path='trend')
    def trend(self, request):
        days = int(request.query_params.get('days', 30))
        data = bodyweight_trend(request.user, days=days)
        serialized = [
            {**entry, 'date': entry['date'].isoformat()}
            for entry in data
        ]
        return Response(serialized)


class BodyCompositionViewSet(viewsets.ModelViewSet):
    serializer_class = BodyCompositionEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return BodyCompositionEntry.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class HeartRateViewSet(viewsets.ModelViewSet):
    serializer_class = HeartRateEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return HeartRateEntry.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CardioViewSet(viewsets.ModelViewSet):
    serializer_class = CardioSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CardioSession.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class NutritionTargetsViewSet(viewsets.ModelViewSet):
    serializer_class = NutritionTargetSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return NutritionTarget.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'], url_path='recompute')
    def recompute(self, request):
        return Response({'task_id': 'placeholder-not-implemented'}, status=status.HTTP_202_ACCEPTED)


class GoalViewSet(viewsets.ModelViewSet):
    serializer_class = GoalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Goal.objects.filter(user=self.request.user)
        goal_status = self.request.query_params.get('status')
        if goal_status in ('active', 'achieved', 'abandoned'):
            qs = qs.filter(status=goal_status)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='transition')
    def transition(self, request, pk=None):
        return Response({'task_id': 'placeholder-not-implemented'}, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['get'], url_path='timeline')
    def timeline(self, request):
        goals = Goal.objects.filter(user=request.user).order_by('-created_at')
        serializer = GoalSerializer(goals, many=True)
        return Response(serializer.data)


class ReportViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WeeklyReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WeeklyReport.objects.filter(user=self.request.user)


class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        # Bodyweight trend (last 30 days)
        bw_trend = bodyweight_trend(user, days=30)

        # Body composition latest
        bc_latest = BodyCompositionEntry.objects.filter(user=user).order_by('-date').first()
        bc_summary = {
            'body_fat_pct': float(bc_latest.body_fat_pct) if bc_latest and bc_latest.body_fat_pct else None,
            'lean_mass': float(bc_latest.lean_mass) if bc_latest and bc_latest.lean_mass else None,
            'date': bc_latest.date.isoformat() if bc_latest else None,
        }

        # Estimated 1RM for main lifts (bench, squat, deadlift by name icontains)
        from training.models import SessionSet
        main_lifts = ['bench press', 'squat', 'deadlift']
        est_1rm_per_lift = {}
        for lift_name in main_lifts:
            latest_set = (
                SessionSet.objects
                .filter(
                    session__user=user,
                    exercise__name__icontains=lift_name,
                    set_type='working',
                )
                .order_by('-session__date', '-set_index')
                .first()
            )
            if latest_set:
                est_1rm_per_lift[lift_name] = estimate_1rm(float(latest_set.weight), latest_set.reps)
            else:
                est_1rm_per_lift[lift_name] = None

        # Weekly volume
        weekly_volume = weekly_volume_by_muscle(user, week_start, week_end)

        # Cardio zone trends (last 8 weeks)
        cardio_zones = zone_minutes_trend(user, weeks=8)
        cardio_zones_serialized = [
            {
                'week_start': w['week_start'].isoformat(),
                'z2_minutes': w['z2_minutes'],
                'total_zone_minutes': w['total_zone_minutes'],
            }
            for w in cardio_zones
        ]

        # Adherence (last 28 days)
        adherence_start = today - timedelta(days=27)
        adh = adherence(user, adherence_start, today)

        # Active goals with progress
        active_goals = Goal.objects.filter(user=user, status='active')
        goals_with_progress = []
        for g in active_goals:
            try:
                progress = goal_progress(g)
            except Exception:
                progress = None
            goals_with_progress.append({
                'id': g.id,
                'title': g.title,
                'goal_type': g.goal_type,
                'target_date': g.target_date.isoformat() if g.target_date else None,
                'progress': progress,
            })

        return Response({
            'bodyweight_trend': [
                {**e, 'date': e['date'].isoformat()} for e in bw_trend
            ],
            'body_composition': bc_summary,
            'est_1rm_main_lifts': est_1rm_per_lift,
            'weekly_volume_by_muscle': weekly_volume,
            'cardio_zone_trends': cardio_zones_serialized,
            'adherence': adh,
            'active_goals': goals_with_progress,
        })


class TaskStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        from celery.result import AsyncResult
        result = AsyncResult(task_id)
        return Response({
            'task_id': task_id,
            'status': result.status,
            'result': result.result if result.ready() and not result.failed() else None,
            'error': str(result.result) if result.failed() else None,
        })
