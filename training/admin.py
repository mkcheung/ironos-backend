from django.contrib import admin

from .models import (
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


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'primary_muscle', 'equipment', 'is_custom', 'created_by')
    list_filter = ('category', 'is_custom')
    search_fields = ('name', 'primary_muscle', 'equipment')


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'goal', 'status', 'length_weeks', 'start_date', 'created_at')
    list_filter = ('status',)
    search_fields = ('name', 'user__username', 'goal')
    date_hierarchy = 'start_date'


@admin.register(ProgramDay)
class ProgramDayAdmin(admin.ModelAdmin):
    list_display = ('name', 'program', 'week_number', 'day_number', 'is_rest', 'focus')
    list_filter = ('is_rest',)
    search_fields = ('name', 'program__name')


@admin.register(ProgramExercise)
class ProgramExerciseAdmin(admin.ModelAdmin):
    list_display = (
        'exercise', 'program_day', 'order', 'target_sets',
        'target_reps_low', 'target_reps_high', 'target_rpe',
    )
    list_filter = ('exercise__category',)
    search_fields = ('exercise__name', 'program_day__name')


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'program_day', 'duration_minutes', 'source', 'created_at')
    list_filter = ('source',)
    search_fields = ('user__username', 'notes')
    date_hierarchy = 'date'


@admin.register(SessionSet)
class SessionSetAdmin(admin.ModelAdmin):
    list_display = ('session', 'exercise', 'set_index', 'weight', 'reps', 'rpe', 'set_type', 'is_estimated')
    list_filter = ('set_type', 'is_estimated')
    search_fields = ('exercise__name', 'session__user__username')


@admin.register(BodyweightEntry)
class BodyweightEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'weight')
    search_fields = ('user__username',)
    date_hierarchy = 'date'


@admin.register(BodyCompositionEntry)
class BodyCompositionEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'weight_kg', 'body_fat_pct', 'lean_mass')
    search_fields = ('user__username',)
    date_hierarchy = 'date'


@admin.register(HeartRateEntry)
class HeartRateEntryAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'resting_hr', 'hrv', 'max_hr', 'source')
    list_filter = ('source',)
    search_fields = ('user__username',)
    date_hierarchy = 'date'


@admin.register(CardioSession)
class CardioSessionAdmin(admin.ModelAdmin):
    list_display = (
        'user', 'date', 'modality', 'activity', 'duration_minutes',
        'distance_km', 'avg_heart_rate', 'perceived_exertion',
    )
    list_filter = ('modality',)
    search_fields = ('user__username', 'activity')
    date_hierarchy = 'date'


@admin.register(NutritionTarget)
class NutritionTargetAdmin(admin.ModelAdmin):
    list_display = ('user', 'date_effective', 'tdee', 'calorie_target', 'protein_g', 'carbs_g', 'fat_g')
    search_fields = ('user__username',)
    date_hierarchy = 'date_effective'


@admin.register(WeeklyReport)
class WeeklyReportAdmin(admin.ModelAdmin):
    list_display = ('user', 'week_start', 'generation_task_id', 'created_at')
    search_fields = ('user__username',)
    date_hierarchy = 'week_start'


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'goal_type', 'status', 'target_date', 'created_at')
    list_filter = ('goal_type', 'status')
    search_fields = ('user__username', 'title')
    # Goal is an append-only state machine; transitions happen in code, not via the admin form
    readonly_fields = ('created_at', 'status_changed_at', 'superseded_by')
