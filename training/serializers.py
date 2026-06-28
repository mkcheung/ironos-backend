from rest_framework import serializers

from training import analytics
from training.models import (
    BodyCompositionEntry,
    BodyweightEntry,
    CardioSession,
    Exercise,
    Goal,
    HeartRateEntry,
    NutritionTarget,
    Program,
    ProgramDay,
    ProgramExercise,
    Session,
    SessionSet,
    WeeklyReport,
)


class ExerciseSerializer(serializers.ModelSerializer):
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Exercise
        fields = [
            'id',
            'name',
            'wger_id',
            'primary_muscle',
            'secondary_muscles',
            'category',
            'equipment',
            'is_custom',
            'created_by',
        ]


class ProgramExerciseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgramExercise
        fields = [
            'id',
            'program_day',
            'exercise',
            'order',
            'target_sets',
            'target_reps_low',
            'target_reps_high',
            'target_rpe',
            'target_weight',
            'notes',
        ]


class ProgramDaySerializer(serializers.ModelSerializer):
    exercises = ProgramExerciseSerializer(many=True, read_only=True)

    class Meta:
        model = ProgramDay
        fields = [
            'id',
            'program',
            'week_number',
            'day_number',
            'name',
            'is_rest',
            'focus',
            'exercises',
        ]


class ProgramSerializer(serializers.ModelSerializer):
    days = ProgramDaySerializer(many=True, read_only=True)

    class Meta:
        model = Program
        fields = [
            'id',
            'user',
            'name',
            'goal',
            'start_date',
            'length_weeks',
            'status',
            'generation_task_id',
            'meta',
            'created_at',
            'days',
        ]
        read_only_fields = ['user', 'generation_task_id', 'created_at']


class SessionSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionSet
        fields = [
            'id',
            'session',
            'exercise',
            'set_index',
            'weight',
            'reps',
            'rpe',
            'set_type',
            'is_estimated',
        ]

    def validate_weight(self, value):
        if not (0 < float(value) <= 1500):
            raise serializers.ValidationError(
                'weight must be greater than 0 and at most 1500 kg.'
            )
        return value

    def validate_reps(self, value):
        if not (1 <= value <= 100):
            raise serializers.ValidationError('reps must be between 1 and 100.')
        return value

    def validate_rpe(self, value):
        if value is not None and not (1.0 <= float(value) <= 10.0):
            raise serializers.ValidationError('rpe must be between 1.0 and 10.0.')
        return value


class SessionSerializer(serializers.ModelSerializer):
    sets = SessionSetSerializer(many=True, read_only=True)

    class Meta:
        model = Session
        fields = [
            'id',
            'user',
            'date',
            'program_day',
            'duration_minutes',
            'notes',
            'source',
            'created_at',
            'sets',
        ]
        read_only_fields = ['user', 'created_at']


class BodyweightEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = BodyweightEntry
        fields = ['id', 'user', 'date', 'weight']
        read_only_fields = ['user']

    def validate_weight(self, value):
        if not (0 < float(value) <= 500):
            raise serializers.ValidationError(
                'weight must be greater than 0 and at most 500 kg.'
            )
        return value


class BodyCompositionEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = BodyCompositionEntry
        fields = [
            'id',
            'user',
            'date',
            'weight_kg',
            'body_fat_pct',
            'lean_mass',
            'measurements',
        ]
        read_only_fields = ['user']

    def validate_body_fat_pct(self, value):
        if value is not None and not (1 <= float(value) <= 70):
            raise serializers.ValidationError(
                'body_fat_pct must be between 1 and 70.'
            )
        return value

    def validate_lean_mass(self, value):
        if value is not None and float(value) <= 0:
            raise serializers.ValidationError('lean_mass must be greater than 0.')
        return value


class HeartRateEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = HeartRateEntry
        fields = ['id', 'user', 'date', 'resting_hr', 'hrv', 'max_hr', 'source']
        read_only_fields = ['user']

    def validate_resting_hr(self, value):
        if value is not None and not (30 <= value <= 200):
            raise serializers.ValidationError(
                'resting_hr must be between 30 and 200.'
            )
        return value

    def validate_max_hr(self, value):
        if value is not None and not (100 <= value <= 250):
            raise serializers.ValidationError('max_hr must be between 100 and 250.')
        return value


class CardioSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardioSession
        fields = [
            'id',
            'user',
            'date',
            'modality',
            'activity',
            'duration_minutes',
            'distance_km',
            'avg_heart_rate',
            'max_heart_rate',
            'avg_pace',
            'pace_unit',
            'splits',
            'zone_minutes',
            'zone_bounds',
            'perceived_exertion',
            'notes',
        ]
        read_only_fields = ['user']

    def validate_duration_minutes(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                'duration_minutes must be greater than 0.'
            )
        return value

    def validate_distance_km(self, value):
        if value is not None and float(value) <= 0:
            raise serializers.ValidationError('distance_km must be greater than 0.')
        return value


class NutritionTargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = NutritionTarget
        fields = [
            'id',
            'user',
            'date_effective',
            'tdee',
            'calorie_target',
            'protein_g',
            'carbs_g',
            'fat_g',
            'rationale',
        ]
        read_only_fields = ['user']

    def validate_calorie_target(self, value):
        if not (500 <= float(value) <= 10000):
            raise serializers.ValidationError(
                'calorie_target must be between 500 and 10000.'
            )
        return value

    def validate_protein_g(self, value):
        if float(value) <= 0:
            raise serializers.ValidationError('protein_g must be greater than 0.')
        return value


class WeeklyReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeeklyReport
        fields = [
            'id',
            'user',
            'week_start',
            'summary_markdown',
            'metrics',
            'generation_task_id',
            'created_at',
        ]
        read_only_fields = ['user', 'generation_task_id', 'created_at']


class GoalSerializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Goal
        fields = [
            'id',
            'user',
            'goal_type',
            'title',
            'exercise',
            'target_mode',
            'target_value',
            'target_reps',
            'target_weight',
            'target_bodyfat',
            'baseline_value',
            'target_date',
            'status',
            'status_changed_at',
            'superseded_by',
            'created_at',
            'progress',
        ]
        read_only_fields = ['user', 'status_changed_at', 'created_at']

    def validate_target_value(self, value):
        if value is not None and float(value) <= 0:
            raise serializers.ValidationError('target_value must be greater than 0.')
        return value

    def get_progress(self, instance):
        try:
            return analytics.goal_progress(instance)
        except Exception:
            return None
