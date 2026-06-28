from datetime import date, timedelta
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from training.models import (
    BodyweightEntry, BodyCompositionEntry, HeartRateEntry,
    CardioSession, NutritionTarget, Goal, Exercise, Session, SessionSet
)


class BodyweightAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user('u1', password='pw')
        self.client.force_authenticate(user=self.user)

    def test_list_bodyweight(self):
        BodyweightEntry.objects.create(user=self.user, date=date.today(), weight=75.0)
        r = self.client.get('/api/bodyweight/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data['results']), 1)

    def test_create_bodyweight(self):
        r = self.client.post('/api/bodyweight/', {'date': date.today().isoformat(), 'weight': 75.0})
        self.assertEqual(r.status_code, 201)

    def test_scoped_to_user(self):
        other = User.objects.create_user('u2', password='pw')
        BodyweightEntry.objects.create(user=other, date=date.today(), weight=80.0)
        r = self.client.get('/api/bodyweight/')
        self.assertEqual(len(r.data['results']), 0)

    def test_trend_endpoint(self):
        BodyweightEntry.objects.create(user=self.user, date=date.today(), weight=75.0)
        r = self.client.get('/api/bodyweight/trend/')
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.data, list)


class GoalAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user('u1', password='pw')
        self.client.force_authenticate(user=self.user)

    def test_create_goal(self):
        r = self.client.post('/api/goals/', {
            'goal_type': 'bodyweight',
            'title': 'Lose 5kg',
            'baseline_value': '80.00',
            'target_value': '75.00',
            'status': 'active',
        })
        self.assertEqual(r.status_code, 201)

    def test_goal_transition_returns_202(self):
        goal = Goal.objects.create(
            user=self.user,
            goal_type='bodyweight',
            title='Test',
            baseline_value=80,
            status='active',
        )
        r = self.client.post(f'/api/goals/{goal.id}/transition/')
        self.assertEqual(r.status_code, 202)

    def test_goals_scoped_to_user(self):
        other = User.objects.create_user('u2', password='pw')
        Goal.objects.create(user=other, goal_type='bodyweight', title='Other', baseline_value=80, status='active')
        r = self.client.get('/api/goals/')
        self.assertEqual(len(r.data['results']), 0)


class DashboardAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user('u1', password='pw')
        self.client.force_authenticate(user=self.user)

    def test_dashboard_returns_200(self):
        r = self.client.get('/api/dashboard/summary/')
        self.assertEqual(r.status_code, 200)

    def test_dashboard_has_required_keys(self):
        r = self.client.get('/api/dashboard/summary/')
        for key in ['bodyweight_trend', 'body_composition', 'est_1rm_main_lifts',
                     'weekly_volume_by_muscle', 'cardio_zone_trends', 'adherence', 'active_goals']:
            self.assertIn(key, r.data)


class NutritionAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user('u1', password='pw')
        self.client.force_authenticate(user=self.user)

    def test_create_nutrition_target(self):
        from datetime import date
        r = self.client.post('/api/nutrition/targets/', {
            'date_effective': date.today().isoformat(),
            'tdee': '2500.00',
            'calorie_target': '2200.00',
            'protein_g': '180.00',
            'carbs_g': '220.00',
            'fat_g': '70.00',
        })
        self.assertEqual(r.status_code, 201)

    def test_recompute_returns_202(self):
        r = self.client.post('/api/nutrition/targets/recompute/')
        self.assertEqual(r.status_code, 202)
