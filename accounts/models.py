from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    UNITS_CHOICES = [
        ('metric', 'Metric'),
        ('imperial', 'Imperial'),
    ]
    SEX_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    EXPERIENCE_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    GOAL_CHOICES = [
        ('fat_loss', 'Fat Loss'),
        ('lean_bulk', 'Lean Bulk'),
        ('recomp', 'Recomp'),
        ('maintenance', 'Maintenance'),
        ('general', 'General'),
    ]
    EQUIPMENT_CHOICES = [
        ('full_gym', 'Full Gym'),
        ('home_gym', 'Home Gym'),
        ('dumbbells_only', 'Dumbbells Only'),
        ('bodyweight', 'Bodyweight'),
    ]
    ACTIVITY_CHOICES = [
        ('sedentary', 'Sedentary'),
        ('lightly_active', 'Lightly Active'),
        ('moderately_active', 'Moderately Active'),
        ('very_active', 'Very Active'),
        ('extremely_active', 'Extremely Active'),
    ]
    LLM_PROVIDER_CHOICES = [
        ('anthropic', 'Anthropic'),
        ('openai', 'OpenAI'),
        ('google', 'Google'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    units = models.CharField(max_length=10, choices=UNITS_CHOICES, default='metric')
    date_of_birth = models.DateField(null=True, blank=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    sex = models.CharField(max_length=10, choices=SEX_CHOICES, null=True, blank=True)
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_CHOICES, default='beginner')
    primary_goal = models.CharField(max_length=20, choices=GOAL_CHOICES, default='general')
    equipment_access = models.CharField(max_length=20, choices=EQUIPMENT_CHOICES, default='full_gym')
    activity_level = models.CharField(max_length=20, choices=ACTIVITY_CHOICES, default='sedentary')
    weekly_training_days = models.PositiveSmallIntegerField(default=3)
    resting_heart_rate = models.PositiveSmallIntegerField(null=True, blank=True)
    max_heart_rate = models.PositiveSmallIntegerField(null=True, blank=True)
    llm_provider = models.CharField(max_length=20, choices=LLM_PROVIDER_CHOICES, default='anthropic')
    llm_provider_locked = models.BooleanField(default=False)
    monthly_token_budget = models.PositiveIntegerField(null=True, blank=True)
    onboarding_complete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile({self.user.username})"
