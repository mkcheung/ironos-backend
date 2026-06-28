"""
Comprehensive unit tests for training/analytics.py.

Tests verify exact numeric outputs for known inputs.
"""

import datetime
from datetime import date

import pytest
from django.contrib.auth.models import User
from django.test import TestCase

from accounts.models import UserProfile
from training.models import (
    BodyweightEntry,
    CardioSession,
    Exercise,
    Goal,
    HeartRateEntry,
    NutritionTarget,
    Session,
    SessionSet,
)
from training import analytics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(username='testuser'):
    return User.objects.create_user(username=username, password='pw')


def _make_exercise(name='Bench Press', primary_muscle='chest'):
    return Exercise.objects.create(
        name=name,
        primary_muscle=primary_muscle,
        secondary_muscles=[],
        category='compound',
        equipment='barbell',
    )


def _make_session(user, session_date=None):
    if session_date is None:
        session_date = date.today()
    return Session.objects.create(user=user, date=session_date)


def _make_set(session, exercise, weight, reps, set_type='working', set_index=1):
    return SessionSet.objects.create(
        session=session,
        exercise=exercise,
        weight=weight,
        reps=reps,
        set_type=set_type,
        set_index=set_index,
    )


# ---------------------------------------------------------------------------
# 1. estimate_1rm
# ---------------------------------------------------------------------------

class TestEstimate1rm(TestCase):

    def test_epley_5_reps(self):
        result = analytics.estimate_1rm(100, 5, formula='epley')
        self.assertAlmostEqual(result, 116.67, places=2)

    def test_epley_1_rep_returns_weight_directly(self):
        result = analytics.estimate_1rm(100, 1, formula='epley')
        self.assertAlmostEqual(result, 100.0, places=2)

    def test_epley_10_reps(self):
        result = analytics.estimate_1rm(80, 10, formula='epley')
        self.assertAlmostEqual(result, 106.67, places=2)

    def test_brzycki_5_reps(self):
        result = analytics.estimate_1rm(100, 5, formula='brzycki')
        self.assertAlmostEqual(result, 112.5, places=2)

    def test_brzycki_1_rep(self):
        result = analytics.estimate_1rm(100, 1, formula='brzycki')
        self.assertAlmostEqual(result, 100.0, places=2)

    def test_brzycki_reps_37_raises_value_error(self):
        with self.assertRaises(ValueError):
            analytics.estimate_1rm(100, 37, formula='brzycki')

    def test_brzycki_reps_above_37_raises_value_error(self):
        with self.assertRaises(ValueError):
            analytics.estimate_1rm(100, 38, formula='brzycki')

    def test_epley_default_formula(self):
        # Default formula should be epley
        result = analytics.estimate_1rm(100, 5)
        self.assertAlmostEqual(result, 116.67, places=2)


# ---------------------------------------------------------------------------
# 2. weekly_volume_by_muscle
# ---------------------------------------------------------------------------

class TestWeeklyVolumeByMuscle(TestCase):

    def test_basic_volume(self):
        user = _make_user()
        exercise = _make_exercise(primary_muscle='chest')
        session = _make_session(user)
        _make_set(session, exercise, weight=100, reps=5, set_type='working')

        start = date.today() - datetime.timedelta(days=6)
        end = date.today()

        result = analytics.weekly_volume_by_muscle(user, start, end)
        self.assertEqual(result.get('chest'), 500.0)

    def test_warmup_sets_excluded(self):
        user = _make_user()
        exercise = _make_exercise(primary_muscle='chest')
        session = _make_session(user)
        _make_set(session, exercise, weight=100, reps=5, set_type='working', set_index=1)
        _make_set(session, exercise, weight=60, reps=10, set_type='warmup', set_index=2)

        start = date.today() - datetime.timedelta(days=6)
        end = date.today()

        result = analytics.weekly_volume_by_muscle(user, start, end)
        # Only working set counted: 100*5 = 500
        self.assertEqual(result.get('chest'), 500.0)

    def test_multiple_muscles(self):
        user = _make_user()
        chest_ex = _make_exercise(name='Bench Press', primary_muscle='chest')
        back_ex = _make_exercise(name='Row', primary_muscle='back')
        session = _make_session(user)
        _make_set(session, chest_ex, weight=100, reps=5, set_type='working', set_index=1)
        _make_set(session, back_ex, weight=80, reps=8, set_type='working', set_index=2)

        start = date.today() - datetime.timedelta(days=6)
        end = date.today()

        result = analytics.weekly_volume_by_muscle(user, start, end)
        self.assertEqual(result.get('chest'), 500.0)
        self.assertEqual(result.get('back'), 640.0)

    def test_sessions_outside_range_excluded(self):
        user = _make_user()
        exercise = _make_exercise(primary_muscle='chest')
        old_date = date.today() - datetime.timedelta(days=30)
        session = _make_session(user, session_date=old_date)
        _make_set(session, exercise, weight=100, reps=5, set_type='working')

        start = date.today() - datetime.timedelta(days=6)
        end = date.today()

        result = analytics.weekly_volume_by_muscle(user, start, end)
        self.assertNotIn('chest', result)

    def test_only_other_users_sets_excluded(self):
        user = _make_user(username='user1')
        other = _make_user(username='user2')
        exercise = _make_exercise(primary_muscle='chest')
        session = _make_session(other)
        _make_set(session, exercise, weight=100, reps=5, set_type='working')

        start = date.today() - datetime.timedelta(days=6)
        end = date.today()

        result = analytics.weekly_volume_by_muscle(user, start, end)
        self.assertNotIn('chest', result)


# ---------------------------------------------------------------------------
# 3. lift_history
# ---------------------------------------------------------------------------

class TestLiftHistory(TestCase):

    def test_returns_correct_fields(self):
        user = _make_user()
        exercise = _make_exercise()
        session = _make_session(user)
        _make_set(session, exercise, weight=100, reps=5, set_type='working')

        history = analytics.lift_history(user, exercise)
        self.assertEqual(len(history), 1)
        entry = history[0]
        self.assertIn('date', entry)
        self.assertIn('weight', entry)
        self.assertIn('reps', entry)
        self.assertIn('estimated_1rm', entry)

    def test_estimated_1rm_correct(self):
        user = _make_user()
        exercise = _make_exercise()
        session = _make_session(user)
        _make_set(session, exercise, weight=100, reps=5, set_type='working')

        history = analytics.lift_history(user, exercise)
        # epley: 100 * (1 + 5/30) = 116.67
        self.assertAlmostEqual(float(history[0]['estimated_1rm']), 116.67, places=2)

    def test_ordering_most_recent_first(self):
        user = _make_user()
        exercise = _make_exercise()
        older_date = date.today() - datetime.timedelta(days=5)
        newer_date = date.today()

        older_session = _make_session(user, session_date=older_date)
        newer_session = _make_session(user, session_date=newer_date)
        _make_set(older_session, exercise, weight=90, reps=5)
        _make_set(newer_session, exercise, weight=100, reps=5)

        history = analytics.lift_history(user, exercise)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]['date'], newer_date)
        self.assertEqual(history[1]['date'], older_date)

    def test_limit_respected(self):
        user = _make_user()
        exercise = _make_exercise()
        for i in range(25):
            session = _make_session(user, session_date=date.today() - datetime.timedelta(days=i))
            _make_set(session, exercise, weight=100, reps=5)

        history = analytics.lift_history(user, exercise, limit=20)
        self.assertEqual(len(history), 20)

    def test_custom_limit(self):
        user = _make_user()
        exercise = _make_exercise()
        for i in range(10):
            session = _make_session(user, session_date=date.today() - datetime.timedelta(days=i))
            _make_set(session, exercise, weight=100, reps=5)

        history = analytics.lift_history(user, exercise, limit=5)
        self.assertEqual(len(history), 5)

    def test_weight_and_reps_correct(self):
        user = _make_user()
        exercise = _make_exercise()
        session = _make_session(user)
        _make_set(session, exercise, weight=80, reps=10)

        history = analytics.lift_history(user, exercise)
        self.assertEqual(float(history[0]['weight']), 80.0)
        self.assertEqual(history[0]['reps'], 10)


# ---------------------------------------------------------------------------
# 4. tdee
# ---------------------------------------------------------------------------

class TestTdee(TestCase):
    """
    UserProfile is auto-created by signal when User is created, so we update
    the existing profile's fields rather than calling .create() again.
    """

    def _age_30_dob(self):
        today = date.today()
        return date(today.year - 30, today.month, today.day)

    def test_male_sedentary_no_cardio(self):
        user = _make_user()
        profile = user.profile
        profile.sex = 'male'
        profile.height_cm = 175
        profile.date_of_birth = self._age_30_dob()
        profile.activity_level = 'sedentary'
        profile.save()
        BodyweightEntry.objects.create(user=user, date=date.today(), weight=80)

        result = analytics.tdee(user)
        # BMR_male = 10*80 + 6.25*175 - 5*30 + 5 = 800 + 1093.75 - 150 + 5 = 1748.75
        # TDEE = 1748.75 * 1.2 = 2098.5
        self.assertAlmostEqual(result, 2098.5, places=1)

    def test_female_sedentary_no_cardio(self):
        user = _make_user(username='femaleuser')
        profile = user.profile
        profile.sex = 'female'
        profile.height_cm = 175
        profile.date_of_birth = self._age_30_dob()
        profile.activity_level = 'sedentary'
        profile.save()
        BodyweightEntry.objects.create(user=user, date=date.today(), weight=80)

        result = analytics.tdee(user)
        # BMR_female = 10*80 + 6.25*175 - 5*30 - 161 = 800 + 1093.75 - 150 - 161 = 1582.75
        # TDEE = 1582.75 * 1.2 = 1899.3
        self.assertAlmostEqual(result, 1899.3, places=1)

    def test_raises_value_error_if_no_bodyweight_entry(self):
        user = _make_user(username='nobwuser')
        profile = user.profile
        profile.sex = 'male'
        profile.height_cm = 175
        profile.date_of_birth = self._age_30_dob()
        profile.activity_level = 'sedentary'
        profile.save()
        with self.assertRaises(ValueError):
            analytics.tdee(user)


# ---------------------------------------------------------------------------
# 5. bodyweight_trend
# ---------------------------------------------------------------------------

class TestBodyweightTrend(TestCase):

    def test_rolling_avg_none_for_first_six_entries(self):
        user = _make_user()
        today = date.today()
        for i in range(10):
            BodyweightEntry.objects.create(
                user=user,
                date=today - datetime.timedelta(days=9 - i),
                weight=80 + i * 0.1,
            )

        result = analytics.bodyweight_trend(user, days=30)
        self.assertEqual(len(result), 10)

        # First 6 entries (index 0..5) should have rolling_avg = None
        for entry in result[:6]:
            self.assertIsNone(entry['rolling_avg'], f"Expected None for early entry, got {entry['rolling_avg']}")

        # Entry at index 6 (7th data point) and beyond should have a value
        for entry in result[6:]:
            self.assertIsNotNone(entry['rolling_avg'])

    def test_ordering_oldest_to_newest(self):
        user = _make_user()
        today = date.today()
        for i in range(5):
            BodyweightEntry.objects.create(
                user=user,
                date=today - datetime.timedelta(days=4 - i),
                weight=80 + i,
            )

        result = analytics.bodyweight_trend(user, days=30)
        dates = [entry['date'] for entry in result]
        self.assertEqual(dates, sorted(dates))

    def test_returns_correct_fields(self):
        user = _make_user()
        BodyweightEntry.objects.create(user=user, date=date.today(), weight=80)

        result = analytics.bodyweight_trend(user, days=30)
        self.assertEqual(len(result), 1)
        entry = result[0]
        self.assertIn('date', entry)
        self.assertIn('weight', entry)
        self.assertIn('rolling_avg', entry)

    def test_days_limit_respected(self):
        user = _make_user()
        today = date.today()
        # Create 60 entries
        for i in range(60):
            BodyweightEntry.objects.create(
                user=user,
                date=today - datetime.timedelta(days=59 - i),
                weight=80,
            )

        result = analytics.bodyweight_trend(user, days=30)
        # Should only include entries within last 30 days
        for entry in result:
            self.assertGreaterEqual(entry['date'], today - datetime.timedelta(days=30))


# ---------------------------------------------------------------------------
# 6. adherence
# ---------------------------------------------------------------------------

class TestAdherence(TestCase):

    def test_3_sessions_in_7_days(self):
        user = _make_user()
        today = date.today()
        start = today - datetime.timedelta(days=6)
        end = today

        # Create 3 sessions in the 7-day window
        for delta in [0, 2, 4]:
            _make_session(user, session_date=start + datetime.timedelta(days=delta))

        result = analytics.adherence(user, start, end)

        self.assertEqual(result['scheduled_days'], 7)
        self.assertEqual(result['completed_days'], 3)
        self.assertAlmostEqual(result['rate'], 0.4286, places=4)

    def test_no_sessions(self):
        user = _make_user()
        today = date.today()
        start = today - datetime.timedelta(days=6)
        end = today

        result = analytics.adherence(user, start, end)
        self.assertEqual(result['completed_days'], 0)
        self.assertAlmostEqual(result['rate'], 0.0, places=4)

    def test_all_days_completed(self):
        user = _make_user()
        today = date.today()
        start = today - datetime.timedelta(days=6)
        end = today

        for delta in range(7):
            _make_session(user, session_date=start + datetime.timedelta(days=delta))

        result = analytics.adherence(user, start, end)
        self.assertEqual(result['completed_days'], 7)
        self.assertAlmostEqual(result['rate'], 1.0, places=4)

    def test_returns_correct_keys(self):
        user = _make_user()
        today = date.today()
        start = today - datetime.timedelta(days=6)
        end = today

        result = analytics.adherence(user, start, end)
        self.assertIn('scheduled_days', result)
        self.assertIn('completed_days', result)
        self.assertIn('rate', result)


# ---------------------------------------------------------------------------
# 7. goal_progress
# ---------------------------------------------------------------------------

class TestGoalProgress(TestCase):

    def test_strength_goal_50_percent(self):
        user = _make_user()
        exercise = _make_exercise()
        goal = Goal.objects.create(
            user=user,
            goal_type='strength',
            title='Bench 120kg',
            exercise=exercise,
            baseline_value=100,
            target_value=120,
        )

        # Create a session set with weight=110, reps=1 → 1RM = 110.0
        session = _make_session(user)
        _make_set(session, exercise, weight=110, reps=1, set_type='working')

        result = analytics.goal_progress(goal)

        self.assertAlmostEqual(float(result['baseline']), 100.0, places=2)
        self.assertAlmostEqual(float(result['current']), 110.0, places=2)
        self.assertAlmostEqual(float(result['target']), 120.0, places=2)
        # percent_to_target = (110 - 100) / (120 - 100) * 100 = 50.0
        self.assertAlmostEqual(float(result['percent_to_target']), 50.0, places=1)

    def test_bodyweight_goal_50_percent(self):
        user = _make_user()
        goal = Goal.objects.create(
            user=user,
            goal_type='bodyweight',
            title='Lose weight to 80kg',
            baseline_value=90,
            target_value=80,
        )
        BodyweightEntry.objects.create(user=user, date=date.today(), weight=85)

        result = analytics.goal_progress(goal)

        # percent_to_target: going from 90→80, current is 85 → (90-85)/(90-80)*100 = 50.0
        self.assertAlmostEqual(float(result['percent_to_target']), 50.0, places=1)
        self.assertAlmostEqual(float(result['baseline']), 90.0, places=2)
        self.assertAlmostEqual(float(result['current']), 85.0, places=2)
        self.assertAlmostEqual(float(result['target']), 80.0, places=2)

    def test_goal_progress_returns_required_keys(self):
        user = _make_user()
        exercise = _make_exercise()
        goal = Goal.objects.create(
            user=user,
            goal_type='strength',
            title='Test goal',
            exercise=exercise,
            baseline_value=100,
            target_value=120,
        )
        session = _make_session(user)
        _make_set(session, exercise, weight=110, reps=1)

        result = analytics.goal_progress(goal)
        for key in ('baseline', 'current', 'target', 'percent_to_target'):
            self.assertIn(key, result)


# ---------------------------------------------------------------------------
# 8. transition_nutrition
# ---------------------------------------------------------------------------

class TestTransitionNutrition(TestCase):

    def _make_nutrition_target(self, user):
        return NutritionTarget.objects.create(
            user=user,
            date_effective=date.today(),
            tdee=2500,
            calorie_target=2500,
            protein_g=180,
            carbs_g=250,
            fat_g=80,
        )

    def test_fat_loss_transition(self):
        user = _make_user()
        old_target = self._make_nutrition_target(user)

        result = analytics.transition_nutrition(old_target, 'fat_loss')

        # new_target = 2500 - 400 = 2100
        # step = (2100 - 2500) / 3 = -133.33
        # week1 calorie_target = 2500 + 1*(-133.33) = 2366.67
        # week2 calorie_target = 2500 + 2*(-133.33) = 2233.33
        # week3 calorie_target = 2100.0
        # Returns a list of 3 dicts with keys: week, calorie_target, protein_g, notes
        self.assertEqual(len(result), 3)
        self.assertAlmostEqual(float(result[0]['calorie_target']), 2366.7, places=0)
        self.assertAlmostEqual(float(result[1]['calorie_target']), 2233.3, places=0)
        self.assertAlmostEqual(float(result[2]['calorie_target']), 2100.0, places=0)

    def test_lean_bulk_transition(self):
        user = _make_user()
        old_target = self._make_nutrition_target(user)

        result = analytics.transition_nutrition(old_target, 'lean_bulk')

        # new_target = 2500 + 200 = 2700
        # step = (2700 - 2500) / 3 = 66.67
        # week1 calorie_target = 2500 + 1*66.67 = 2566.7
        # week2 calorie_target = 2500 + 2*66.67 = 2633.3
        # week3 calorie_target = 2700.0
        self.assertEqual(len(result), 3)
        self.assertAlmostEqual(float(result[0]['calorie_target']), 2566.7, places=0)
        self.assertAlmostEqual(float(result[1]['calorie_target']), 2633.3, places=0)
        self.assertAlmostEqual(float(result[2]['calorie_target']), 2700.0, places=0)

    def test_returns_3_week_list(self):
        user = _make_user()
        old_target = self._make_nutrition_target(user)

        result = analytics.transition_nutrition(old_target, 'fat_loss')
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        # Each entry should have week number, calorie_target, protein_g, notes
        for i, entry in enumerate(result, start=1):
            self.assertEqual(entry['week'], i)
            self.assertIn('calorie_target', entry)
            self.assertIn('protein_g', entry)
            self.assertIn('notes', entry)


# ---------------------------------------------------------------------------
# 9. zone_minutes_trend
# ---------------------------------------------------------------------------

class TestZoneMinutesTrend(TestCase):

    def test_basic_zone_minutes(self):
        user = _make_user()
        today = date.today()
        CardioSession.objects.create(
            user=user,
            date=today,
            modality='steady',
            activity='run',
            duration_minutes=45,
            zone_minutes={'z1': 10, 'z2': 30, 'z3': 5},
        )

        result = analytics.zone_minutes_trend(user, weeks=4)
        self.assertIsNotNone(result)
        # Should have at least one week entry
        self.assertGreater(len(result), 0)

        # Find the week containing today
        current_week = None
        for week in result:
            if 'z2_minutes' in week or 'total_minutes' in week:
                current_week = week
                break

        # Check totals in the most recent week
        found_week = result[-1] if result else None
        if found_week:
            self.assertIn('week_start', found_week)

    def test_z2_minutes_correct(self):
        user = _make_user()
        today = date.today()
        CardioSession.objects.create(
            user=user,
            date=today,
            modality='steady',
            activity='run',
            duration_minutes=45,
            zone_minutes={'z1': 10, 'z2': 30, 'z3': 5},
        )

        result = analytics.zone_minutes_trend(user, weeks=4)
        # Most recent week should have z2_minutes = 30 and total_zone_minutes = 45
        latest_week = result[-1] if result else None
        self.assertIsNotNone(latest_week)
        self.assertAlmostEqual(float(latest_week.get('z2_minutes', 0)), 30.0, places=1)
        # total_zone_minutes = z1 + z2 + z3 = 10 + 30 + 5 = 45
        self.assertAlmostEqual(float(latest_week.get('total_zone_minutes', 0)), 45.0, places=1)

    def test_weeks_limit(self):
        user = _make_user()
        result = analytics.zone_minutes_trend(user, weeks=4)
        self.assertEqual(len(result), 4)


# ---------------------------------------------------------------------------
# 10. pace_at_heart_rate
# ---------------------------------------------------------------------------

class TestPaceAtHeartRate(TestCase):

    def test_matching_sessions_averaged(self):
        user = _make_user()
        today = date.today()
        CardioSession.objects.create(
            user=user,
            date=today - datetime.timedelta(days=1),
            modality='steady',
            activity='run',
            duration_minutes=30,
            avg_heart_rate=150,
            avg_pace=5.5,
        )
        CardioSession.objects.create(
            user=user,
            date=today,
            modality='steady',
            activity='run',
            duration_minutes=30,
            avg_heart_rate=152,
            avg_pace=5.3,
        )

        # Both are within ±10 bpm of 150 → average = (5.5 + 5.3) / 2 = 5.4
        result = analytics.pace_at_heart_rate(user, 150, weeks=12)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(float(result), 5.4, places=1)

    def test_no_matching_sessions_returns_none(self):
        user = _make_user()
        today = date.today()
        CardioSession.objects.create(
            user=user,
            date=today,
            modality='steady',
            activity='run',
            duration_minutes=30,
            avg_heart_rate=200,  # Far outside ±10 of target
            avg_pace=4.0,
        )

        result = analytics.pace_at_heart_rate(user, 150, weeks=12)
        self.assertIsNone(result)

    def test_empty_returns_none(self):
        user = _make_user()
        result = analytics.pace_at_heart_rate(user, 150, weeks=12)
        self.assertIsNone(result)

    def test_sessions_outside_time_window_excluded(self):
        user = _make_user()
        old_date = date.today() - datetime.timedelta(weeks=13)
        CardioSession.objects.create(
            user=user,
            date=old_date,
            modality='steady',
            activity='run',
            duration_minutes=30,
            avg_heart_rate=150,
            avg_pace=5.5,
        )

        result = analytics.pace_at_heart_rate(user, 150, weeks=12)
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# 11. resting_hr_trend
# ---------------------------------------------------------------------------

class TestRestingHrTrend(TestCase):

    def test_returns_correct_fields(self):
        user = _make_user()
        HeartRateEntry.objects.create(user=user, date=date.today(), resting_hr=60)

        result = analytics.resting_hr_trend(user, days=30)
        self.assertEqual(len(result), 1)
        entry = result[0]
        self.assertIn('date', entry)
        self.assertIn('resting_hr', entry)
        self.assertIn('rolling_avg', entry)

    def test_rolling_avg_none_for_first_six_entries(self):
        user = _make_user()
        today = date.today()
        for i in range(10):
            HeartRateEntry.objects.create(
                user=user,
                date=today - datetime.timedelta(days=9 - i),
                resting_hr=60 + i,
            )

        result = analytics.resting_hr_trend(user, days=30)
        self.assertEqual(len(result), 10)

        # First 6 entries should have rolling_avg = None
        for entry in result[:6]:
            self.assertIsNone(entry['rolling_avg'])

        # 7th entry onward should have a rolling average
        for entry in result[6:]:
            self.assertIsNotNone(entry['rolling_avg'])

    def test_ordering_oldest_to_newest(self):
        user = _make_user()
        today = date.today()
        for i in range(5):
            HeartRateEntry.objects.create(
                user=user,
                date=today - datetime.timedelta(days=4 - i),
                resting_hr=60,
            )

        result = analytics.resting_hr_trend(user, days=30)
        dates = [entry['date'] for entry in result]
        self.assertEqual(dates, sorted(dates))

    def test_days_limit_respected(self):
        user = _make_user()
        today = date.today()
        for i in range(60):
            HeartRateEntry.objects.create(
                user=user,
                date=today - datetime.timedelta(days=59 - i),
                resting_hr=60,
            )

        result = analytics.resting_hr_trend(user, days=30)
        for entry in result:
            self.assertGreaterEqual(entry['date'], today - datetime.timedelta(days=30))

    def test_rolling_avg_value_correct(self):
        user = _make_user()
        today = date.today()
        # Create exactly 7 entries with known values
        values = [60, 62, 61, 63, 60, 61, 62]
        for i, hr in enumerate(values):
            HeartRateEntry.objects.create(
                user=user,
                date=today - datetime.timedelta(days=6 - i),
                resting_hr=hr,
            )

        result = analytics.resting_hr_trend(user, days=30)
        # 7th entry (index 6) should have rolling_avg = mean of all 7
        expected_avg = sum(values) / 7  # = 61.29...
        self.assertIsNotNone(result[6]['rolling_avg'])
        self.assertAlmostEqual(float(result[6]['rolling_avg']), expected_avg, places=1)


# ---------------------------------------------------------------------------
# 12. vo2_max_estimate
# ---------------------------------------------------------------------------

class TestVo2MaxEstimate(TestCase):
    """
    UserProfile is auto-created by signal when User is created, so we update
    the existing profile's fields rather than calling .create() again.
    The analytics function reads max_heart_rate from HeartRateEntry.max_hr first,
    falling back to UserProfile.max_heart_rate if no entry exists.
    """

    def test_basic_estimate(self):
        user = _make_user()
        # Update auto-created profile with max_heart_rate
        profile = user.profile
        profile.max_heart_rate = 190
        profile.save()
        HeartRateEntry.objects.create(user=user, date=date.today(), resting_hr=60)

        result = analytics.vo2_max_estimate(user)
        # 15 * (190 / 60) = 47.5
        self.assertIsNotNone(result)
        self.assertAlmostEqual(float(result), 47.5, places=1)

    def test_returns_none_if_no_max_heart_rate(self):
        user = _make_user()
        # Profile auto-created with max_heart_rate=None (default)
        HeartRateEntry.objects.create(user=user, date=date.today(), resting_hr=60)

        result = analytics.vo2_max_estimate(user)
        self.assertIsNone(result)

    def test_returns_none_if_no_resting_hr(self):
        user = _make_user()
        profile = user.profile
        profile.max_heart_rate = 190
        profile.save()
        # No HeartRateEntry → no resting HR (profile.resting_heart_rate is None by default)

        result = analytics.vo2_max_estimate(user)
        self.assertIsNone(result)

    def test_returns_none_if_no_profile(self):
        user = _make_user()
        # Delete the auto-created profile so there truly is none
        user.profile.delete()

        result = analytics.vo2_max_estimate(user)
        self.assertIsNone(result)

    def test_different_values(self):
        user = _make_user()
        profile = user.profile
        profile.max_heart_rate = 180
        profile.save()
        HeartRateEntry.objects.create(user=user, date=date.today(), resting_hr=50)

        result = analytics.vo2_max_estimate(user)
        # 15 * (180 / 50) = 54.0
        self.assertAlmostEqual(float(result), 54.0, places=1)
