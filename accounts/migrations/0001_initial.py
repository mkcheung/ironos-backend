import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('units', models.CharField(
                    choices=[('metric', 'Metric'), ('imperial', 'Imperial')],
                    default='metric',
                    max_length=10,
                )),
                ('date_of_birth', models.DateField(blank=True, null=True)),
                ('height_cm', models.DecimalField(blank=True, decimal_places=1, max_digits=5, null=True)),
                ('sex', models.CharField(
                    blank=True,
                    choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
                    max_length=10,
                    null=True,
                )),
                ('experience_level', models.CharField(
                    choices=[('beginner', 'Beginner'), ('intermediate', 'Intermediate'), ('advanced', 'Advanced')],
                    default='beginner',
                    max_length=20,
                )),
                ('primary_goal', models.CharField(
                    choices=[
                        ('fat_loss', 'Fat Loss'),
                        ('lean_bulk', 'Lean Bulk'),
                        ('recomp', 'Recomp'),
                        ('maintenance', 'Maintenance'),
                        ('general', 'General'),
                    ],
                    default='general',
                    max_length=20,
                )),
                ('equipment_access', models.CharField(
                    choices=[
                        ('full_gym', 'Full Gym'),
                        ('home_gym', 'Home Gym'),
                        ('dumbbells_only', 'Dumbbells Only'),
                        ('bodyweight', 'Bodyweight'),
                    ],
                    default='full_gym',
                    max_length=20,
                )),
                ('activity_level', models.CharField(
                    choices=[
                        ('sedentary', 'Sedentary'),
                        ('lightly_active', 'Lightly Active'),
                        ('moderately_active', 'Moderately Active'),
                        ('very_active', 'Very Active'),
                        ('extremely_active', 'Extremely Active'),
                    ],
                    default='sedentary',
                    max_length=20,
                )),
                ('weekly_training_days', models.PositiveSmallIntegerField(default=3)),
                ('resting_heart_rate', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('max_heart_rate', models.PositiveSmallIntegerField(blank=True, null=True)),
                ('llm_provider', models.CharField(
                    choices=[('anthropic', 'Anthropic'), ('openai', 'OpenAI'), ('google', 'Google')],
                    default='anthropic',
                    max_length=20,
                )),
                ('llm_provider_locked', models.BooleanField(default=False)),
                ('monthly_token_budget', models.PositiveIntegerField(blank=True, null=True)),
                ('onboarding_complete', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='profile',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
    ]
