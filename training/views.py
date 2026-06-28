from django.db.models import Q
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from training.models import Exercise, Program, Session, SessionSet
from training.serializers import (
    ExerciseSerializer,
    ProgramSerializer,
    SessionSerializer,
    SessionSetSerializer,
)


class ExerciseViewSet(viewsets.ModelViewSet):
    serializer_class = ExerciseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Exercise.objects.filter(
            Q(is_custom=False) | Q(created_by=self.request.user)
        )
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(name__icontains=search) | Q(primary_muscle__icontains=search)
            )
        return qs

    def perform_create(self, serializer):
        serializer.save(is_custom=True, created_by=self.request.user)


class ProgramViewSet(viewsets.ModelViewSet):
    serializer_class = ProgramSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Program.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'], url_path='generate')
    def generate(self, request):
        return Response(
            {'task_id': 'placeholder-not-implemented'},
            status=status.HTTP_202_ACCEPTED,
        )


class SessionViewSet(viewsets.ModelViewSet):
    serializer_class = SessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Session.objects.filter(user=self.request.user)
        date_param = self.request.query_params.get('date')
        if date_param:
            qs = qs.filter(date=date_param)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['post'], url_path='log_from_text')
    def log_from_text(self, request):
        return Response(
            {'task_id': 'placeholder-not-implemented'},
            status=status.HTTP_202_ACCEPTED,
        )


class SessionSetViewSet(viewsets.ModelViewSet):
    serializer_class = SessionSetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = SessionSet.objects.filter(session__user=self.request.user)
        session_id = self.request.query_params.get('session')
        if session_id:
            qs = qs.filter(session_id=session_id)
        return qs

    def perform_create(self, serializer):
        session = serializer.validated_data.get('session')
        if session.user != self.request.user:
            raise serializers.ValidationError(
                {'session': 'You do not have permission to add sets to this session.'}
            )
        serializer.save()
