import datetime

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from training.models import Exercise, Program, Session, SessionSet


class ExerciseAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user('u1', password='pw')
        self.client.force_authenticate(user=self.user)
        Exercise.objects.create(
            name='Bench Press',
            primary_muscle='chest',
            secondary_muscles=[],
            category='compound',
            equipment='barbell',
            is_custom=False,
        )
        Exercise.objects.create(
            name='Leg Press',
            primary_muscle='quads',
            secondary_muscles=[],
            category='compound',
            equipment='machine',
            is_custom=False,
        )

    def test_list_exercises(self):
        response = self.client.get('/api/exercises/')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data['results']), 2)

    def test_search_exercises(self):
        response = self.client.get('/api/exercises/?search=bench')
        self.assertEqual(response.status_code, 200)
        names = [e['name'] for e in response.data['results']]
        self.assertIn('Bench Press', names)
        self.assertNotIn('Leg Press', names)

    def test_search_exercises_by_muscle(self):
        response = self.client.get('/api/exercises/?search=quads')
        self.assertEqual(response.status_code, 200)
        names = [e['name'] for e in response.data['results']]
        self.assertIn('Leg Press', names)

    def test_create_custom_exercise(self):
        data = {
            'name': 'My Custom Curl',
            'primary_muscle': 'biceps',
            'secondary_muscles': [],
            'category': 'isolation',
            'equipment': 'dumbbell',
        }
        response = self.client.post('/api/exercises/', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['is_custom'])
        self.assertEqual(response.data['created_by'], self.user.pk)

    def test_unauthenticated_returns_401(self):
        unauth_client = APIClient()
        response = unauth_client.get('/api/exercises/')
        self.assertEqual(response.status_code, 401)

    def test_custom_exercise_visible_only_to_owner(self):
        other_user = User.objects.create_user('u2', password='pw')
        Exercise.objects.create(
            name='Secret Exercise',
            primary_muscle='lats',
            secondary_muscles=[],
            category='isolation',
            equipment='cable',
            is_custom=True,
            created_by=other_user,
        )
        # u1 should not see u2's custom exercise
        response = self.client.get('/api/exercises/?search=Secret')
        self.assertEqual(response.status_code, 200)
        names = [e['name'] for e in response.data['results']]
        self.assertNotIn('Secret Exercise', names)


class ProgramAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user('u1', password='pw')
        self.client.force_authenticate(user=self.user)

    def test_list_programs_empty(self):
        response = self.client.get('/api/programs/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

    def test_create_program(self):
        data = {
            'name': 'Powerlifting 12wk',
            'goal': 'strength',
            'length_weeks': 12,
        }
        response = self.client.post('/api/programs/', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['name'], 'Powerlifting 12wk')
        self.assertEqual(response.data['user'], self.user.pk)

    def test_program_scoped_to_user(self):
        other_user = User.objects.create_user('u2', password='pw')
        Program.objects.create(
            user=other_user,
            name='Other Program',
            goal='fat_loss',
            length_weeks=8,
        )
        response = self.client.get('/api/programs/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 0)

    def test_generate_action_returns_202(self):
        response = self.client.post('/api/programs/generate/', {}, format='json')
        self.assertEqual(response.status_code, 202)
        self.assertIn('task_id', response.data)

    def test_unauthenticated_returns_401(self):
        unauth_client = APIClient()
        response = unauth_client.get('/api/programs/')
        self.assertEqual(response.status_code, 401)


class SessionAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user('u1', password='pw')
        self.client.force_authenticate(user=self.user)
        Session.objects.create(user=self.user, date='2026-06-01', source='manual')
        Session.objects.create(user=self.user, date='2026-06-15', source='manual')

    def test_list_sessions(self):
        response = self.client.get('/api/sessions/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)

    def test_filter_by_date(self):
        response = self.client.get('/api/sessions/?date=2026-06-01')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['date'], '2026-06-01')

    def test_create_session(self):
        data = {'date': '2026-06-27', 'source': 'manual'}
        response = self.client.post('/api/sessions/', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['user'], self.user.pk)

    def test_sessions_scoped_to_user(self):
        other_user = User.objects.create_user('u2', password='pw')
        Session.objects.create(user=other_user, date='2026-06-10', source='manual')
        response = self.client.get('/api/sessions/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 2)  # only u1's sessions

    def test_log_from_text_returns_202(self):
        response = self.client.post('/api/sessions/log_from_text/', {}, format='json')
        self.assertEqual(response.status_code, 202)
        self.assertIn('task_id', response.data)

    def test_unauthenticated_returns_401(self):
        unauth_client = APIClient()
        response = unauth_client.get('/api/sessions/')
        self.assertEqual(response.status_code, 401)


class SessionSetAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user('u1', password='pw')
        self.client.force_authenticate(user=self.user)
        self.exercise = Exercise.objects.create(
            name='Squat',
            primary_muscle='quads',
            secondary_muscles=[],
            category='compound',
            equipment='barbell',
            is_custom=False,
        )
        self.session = Session.objects.create(
            user=self.user, date='2026-06-27', source='manual'
        )
        SessionSet.objects.create(
            session=self.session,
            exercise=self.exercise,
            set_index=1,
            weight=100,
            reps=5,
            set_type='working',
        )

    def test_list_session_sets(self):
        response = self.client.get('/api/session-sets/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)

    def test_filter_by_session(self):
        other_session = Session.objects.create(
            user=self.user, date='2026-06-26', source='manual'
        )
        SessionSet.objects.create(
            session=other_session,
            exercise=self.exercise,
            set_index=1,
            weight=80,
            reps=8,
            set_type='working',
        )
        response = self.client.get(f'/api/session-sets/?session={self.session.pk}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['session'], self.session.pk)

    def test_create_session_set(self):
        data = {
            'session': self.session.pk,
            'exercise': self.exercise.pk,
            'set_index': 2,
            'weight': '120.00',
            'reps': 3,
            'set_type': 'working',
        }
        response = self.client.post('/api/session-sets/', data, format='json')
        self.assertEqual(response.status_code, 201)

    def test_create_validates_weight_too_high(self):
        data = {
            'session': self.session.pk,
            'exercise': self.exercise.pk,
            'set_index': 3,
            'weight': '2000.00',
            'reps': 1,
            'set_type': 'working',
        }
        response = self.client.post('/api/session-sets/', data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('weight', response.data)

    def test_create_validates_reps_out_of_range(self):
        data = {
            'session': self.session.pk,
            'exercise': self.exercise.pk,
            'set_index': 3,
            'weight': '100.00',
            'reps': 200,
            'set_type': 'working',
        }
        response = self.client.post('/api/session-sets/', data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('reps', response.data)

    def test_create_rejects_other_users_session(self):
        other_user = User.objects.create_user('u2', password='pw')
        other_session = Session.objects.create(
            user=other_user, date='2026-06-27', source='manual'
        )
        data = {
            'session': other_session.pk,
            'exercise': self.exercise.pk,
            'set_index': 1,
            'weight': '60.00',
            'reps': 10,
            'set_type': 'working',
        }
        response = self.client.post('/api/session-sets/', data, format='json')
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_returns_401(self):
        unauth_client = APIClient()
        response = unauth_client.get('/api/session-sets/')
        self.assertEqual(response.status_code, 401)
