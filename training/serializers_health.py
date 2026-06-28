from rest_framework import serializers

from training.models import (
    BodyweightEntry,
    BodyCompositionEntry,
    HeartRateEntry,
    CardioSession,
    NutritionTarget,
    WeeklyReport,
    Goal,
)


class BodyweightEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = BodyweightEntry
        fields = ['id', 'date', 'weight']

    def validate_weight(self, value):
        if not (0 < float(value) <= 500):
            raise serializers.ValidationError('Weight must be in range (0, 500].')
        return value


class BodyCompositionEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = BodyCompositionEntry
        fields = ['id', 'date', 'weight_kg', 'body_fat_pct', 'lean_mass', 'measurements']

    def validate_body_fat_pct(self, value):
        if value is not None and not (1 <= float(value) <= 70):
            raise serializers.ValidationError('Body fat percentage must be in range [1, 70].')
        return value

    def validate_lean_mass(self, value):
        if value is not None and float(value) <= 0:
            raise serializers.ValidationError('Lean mass must be greater than 0.')
        return value


class HeartRateEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = HeartRateEntry
        fields = ['id', 'date', 'resting_hr', 'hrv', 'max_hr', 'source']

    def validate_resting_hr(self, value):
        if value is not None and not (30 <= value <= 200):
            raise serializers.ValidationError('Resting HR must be in range [30, 200].')
        return value

    def validate_max_hr(self, value):
        if value is not None and not (100 <= value <= 250):
            raise serializers.ValidationError('Max HR must be in range [100, 250].')
        return value


class CardioSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardioSession
        fields = [
            'id', 'date', 'modality', 'activity', 'duration_minutes',
            'distance_km', 'avg_heart_rate', 'max_heart_rate', 'avg_pace',
            'pace_unit', 'splits', 'zone_minutes', 'zone_bounds',
            'perceived_exertion', 'notes',
        ]

    def validate_duration_minutes(self, value):
        if value <= 0:
            raise serializers.ValidationError('Duration must be greater than 0.')
        return value

    def validate_distance_km(self, value):
        if value is not None and float(value) <= 0:
            raise serializers.ValidationError('Distance must be greater than 0.')
        return value


class NutritionTargetSerializer(serializers.ModelSerializer):
    class Meta:
        model = NutritionTarget
        fields = [
            'id', 'date_effective', 'tdee', 'calorie_target',
            'protein_g', 'carbs_g', 'fat_g', 'rationale',
        ]

    def validate_calorie_target(self, value):
        if not (500 <= float(value) <= 10000):
            raise serializers.ValidationError('Calorie target must be in range [500, 10000].')
        return value

    def validate_protein_g(self, value):
        if float(value) <= 0:
            raise serializers.ValidationError('Protein must be greater than 0.')
        return value


class WeeklyReportSerializer(serializers.ModelSerializer):
    generation_task_id = serializers.CharField(read_only=True)

    class Meta:
        model = WeeklyReport
        fields = [
            'id', 'week_start', 'summary_markdown', 'metrics',
            'generation_task_id', 'created_at',
        ]


class GoalSerializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()

    class Meta:
        model = Goal
        fields = [
            'id', 'goal_type', 'title', 'exercise', 'target_mode',
            'target_value', 'target_reps', 'target_weight', 'target_bodyfat',
            'baseline_value', 'target_date', 'status', 'status_changed_at',
            'superseded_by', 'created_at', 'progress',
        ]

    def get_progress(self, obj):
        try:
            from training.analytics import goal_progress
            return goal_progress(obj)
        except Exception:
            return None

    def validate_target_value(self, value):
        if value is not None and float(value) <= 0:
            raise serializers.ValidationError('Target value must be greater than 0.')
        return value
