from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    fields = (
        'units', 'date_of_birth', 'height_cm', 'sex',
        'experience_level', 'primary_goal', 'equipment_access', 'activity_level',
        'weekly_training_days', 'resting_heart_rate', 'max_heart_rate',
        'llm_provider', 'llm_provider_locked', 'monthly_token_budget',
        'onboarding_complete',
    )


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'units', 'experience_level', 'primary_goal', 'llm_provider', 'onboarding_complete')
    list_filter = ('units', 'experience_level', 'primary_goal', 'equipment_access', 'activity_level', 'llm_provider')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
