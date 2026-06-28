from django.db import models
from django.contrib.auth.models import User


class Exercise(models.Model):
    CATEGORY_CHOICES = [
        ('compound', 'Compound'),
        ('isolation', 'Isolation'),
        ('cardio', 'Cardio'),
    ]

    name = models.CharField(max_length=255)
    wger_id = models.IntegerField(null=True, blank=True)
    primary_muscle = models.CharField(max_length=100)
    secondary_muscles = models.JSONField(default=list)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    equipment = models.CharField(max_length=100)
    is_custom = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='custom_exercises',
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Program(models.Model):
    STATUS_CHOICES = [
        ('generating', 'Generating'),
        ('active', 'Active'),
        ('archived', 'Archived'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='programs')
    name = models.CharField(max_length=255)
    goal = models.CharField(max_length=255)
    start_date = models.DateField(null=True, blank=True)
    length_weeks = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='generating')
    generation_task_id = models.CharField(max_length=255, null=True, blank=True)
    meta = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} — {self.name}"


class ProgramDay(models.Model):
    program = models.ForeignKey(Program, on_delete=models.CASCADE, related_name='days')
    week_number = models.PositiveSmallIntegerField()
    day_number = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=255)
    is_rest = models.BooleanField(default=False)
    focus = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['week_number', 'day_number']
        unique_together = [('program', 'week_number', 'day_number')]

    def __str__(self):
        return f"{self.program.name} W{self.week_number}D{self.day_number} — {self.name}"


class ProgramExercise(models.Model):
    program_day = models.ForeignKey(ProgramDay, on_delete=models.CASCADE, related_name='exercises')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='program_exercises')
    order = models.PositiveSmallIntegerField()
    target_sets = models.PositiveSmallIntegerField()
    target_reps_low = models.PositiveSmallIntegerField()
    target_reps_high = models.PositiveSmallIntegerField()
    target_rpe = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    target_weight = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.program_day} — {self.exercise.name} x{self.target_sets}"


class Session(models.Model):
    SOURCE_CHOICES = [
        ('manual', 'Manual'),
        ('chat', 'Chat'),
        ('import', 'Import'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    date = models.DateField(db_index=True)
    program_day = models.ForeignKey(
        ProgramDay,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sessions',
    )
    duration_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='manual')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.user.username} session on {self.date}"


class SessionSet(models.Model):
    SET_TYPE_CHOICES = [
        ('working', 'Working'),
        ('warmup', 'Warmup'),
        ('backoff', 'Backoff'),
        ('dropset', 'Dropset'),
        ('failure', 'Failure'),
    ]

    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='sets')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='session_sets')
    set_index = models.PositiveSmallIntegerField()
    weight = models.DecimalField(max_digits=7, decimal_places=2)
    reps = models.PositiveSmallIntegerField()
    rpe = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    set_type = models.CharField(max_length=20, choices=SET_TYPE_CHOICES, default='working')
    is_estimated = models.BooleanField(default=False)

    class Meta:
        ordering = ['set_index']

    def __str__(self):
        return f"{self.session} — {self.exercise.name} set {self.set_index}"


class BodyweightEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bodyweight_entries')
    date = models.DateField(db_index=True)
    weight = models.DecimalField(max_digits=6, decimal_places=2)

    class Meta:
        ordering = ['-date']
        unique_together = [('user', 'date')]

    def __str__(self):
        return f"{self.user.username} BW {self.weight} on {self.date}"


class BodyCompositionEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='body_composition_entries')
    date = models.DateField(db_index=True)
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    body_fat_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    lean_mass = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    measurements = models.JSONField(default=dict)

    class Meta:
        ordering = ['-date']
        unique_together = [('user', 'date')]

    def __str__(self):
        return f"{self.user.username} body comp on {self.date}"


class HeartRateEntry(models.Model):
    SOURCE_CHOICES = [
        ('manual', 'Manual'),
        ('import', 'Import'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='heart_rate_entries')
    date = models.DateField(db_index=True)
    resting_hr = models.PositiveSmallIntegerField(null=True, blank=True)
    hrv = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    max_hr = models.PositiveSmallIntegerField(null=True, blank=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='manual')

    class Meta:
        ordering = ['-date']
        unique_together = [('user', 'date')]

    def __str__(self):
        return f"{self.user.username} HR on {self.date}"


class CardioSession(models.Model):
    MODALITY_CHOICES = [
        ('steady', 'Steady State'),
        ('hiit', 'HIIT'),
        ('sport', 'Sport'),
    ]
    PACE_UNIT_CHOICES = [
        ('min_per_km', 'min/km'),
        ('min_per_mile', 'min/mile'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cardio_sessions')
    date = models.DateField(db_index=True)
    modality = models.CharField(max_length=20, choices=MODALITY_CHOICES)
    activity = models.CharField(max_length=100)
    duration_minutes = models.PositiveSmallIntegerField()
    distance_km = models.DecimalField(max_digits=7, decimal_places=3, null=True, blank=True)
    avg_heart_rate = models.PositiveSmallIntegerField(null=True, blank=True)
    max_heart_rate = models.PositiveSmallIntegerField(null=True, blank=True)
    avg_pace = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    pace_unit = models.CharField(max_length=20, choices=PACE_UNIT_CHOICES, null=True, blank=True)
    splits = models.JSONField(default=list)
    zone_minutes = models.JSONField(default=dict)
    zone_bounds = models.JSONField(null=True, blank=True)
    perceived_exertion = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.username} {self.activity} on {self.date}"


class NutritionTarget(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='nutrition_targets')
    date_effective = models.DateField(db_index=True)
    tdee = models.DecimalField(max_digits=7, decimal_places=2)
    calorie_target = models.DecimalField(max_digits=7, decimal_places=2)
    protein_g = models.DecimalField(max_digits=6, decimal_places=2)
    carbs_g = models.DecimalField(max_digits=6, decimal_places=2)
    fat_g = models.DecimalField(max_digits=6, decimal_places=2)
    rationale = models.TextField(blank=True)

    class Meta:
        ordering = ['-date_effective']

    def __str__(self):
        return f"{self.user.username} nutrition target from {self.date_effective}"


class WeeklyReport(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='weekly_reports')
    week_start = models.DateField(db_index=True)
    summary_markdown = models.TextField(blank=True)
    metrics = models.JSONField(default=dict)
    generation_task_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-week_start']
        unique_together = [('user', 'week_start')]

    def __str__(self):
        return f"{self.user.username} weekly report {self.week_start}"


class Goal(models.Model):
    GOAL_TYPE_CHOICES = [
        ('strength', 'Strength'),
        ('bodyweight', 'Bodyweight'),
        ('body_fat', 'Body Fat'),
        ('performance', 'Performance'),
        ('habit', 'Habit'),
    ]
    TARGET_MODE_CHOICES = [
        ('one_rm', 'One Rep Max'),
        ('weight_for_reps', 'Weight for Reps'),
        ('x_bodyweight', 'X Bodyweight'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('achieved', 'Achieved'),
        ('abandoned', 'Abandoned'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='goals')
    goal_type = models.CharField(max_length=20, choices=GOAL_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    exercise = models.ForeignKey(
        Exercise,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='goals',
    )
    target_mode = models.CharField(max_length=20, choices=TARGET_MODE_CHOICES, null=True, blank=True)
    target_value = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    target_reps = models.PositiveSmallIntegerField(null=True, blank=True)
    target_weight = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    target_bodyfat = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    baseline_value = models.DecimalField(max_digits=8, decimal_places=2)
    target_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    status_changed_at = models.DateTimeField(null=True, blank=True)
    superseded_by = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='supersedes',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} goal: {self.title} ({self.status})"
