from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from rest_framework import serializers
from .models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    weekly_training_days = serializers.IntegerField(
        required=False,
        validators=[MinValueValidator(1), MaxValueValidator(7)],
    )
    resting_heart_rate = serializers.IntegerField(
        required=False,
        allow_null=True,
        validators=[MinValueValidator(30), MaxValueValidator(200)],
    )
    max_heart_rate = serializers.IntegerField(
        required=False,
        allow_null=True,
        validators=[MinValueValidator(100), MaxValueValidator(250)],
    )

    class Meta:
        model = UserProfile
        fields = [
            'units',
            'date_of_birth',
            'height_cm',
            'sex',
            'experience_level',
            'primary_goal',
            'equipment_access',
            'activity_level',
            'weekly_training_days',
            'resting_heart_rate',
            'max_heart_rate',
            'llm_provider',
            'llm_provider_locked',
            'monthly_token_budget',
            'onboarding_complete',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'profile']


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with that username already exists.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with that email already exists.")
        return value

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password2": "Passwords do not match."})
        try:
            validate_password(data['password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
        )
        return user
