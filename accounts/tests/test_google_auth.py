from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.test import override_settings
from google.auth.exceptions import GoogleAuthError
from rest_framework.test import APIClient


GOOGLE_ENDPOINT = '/api/auth/google/'

VALID_IDINFO = {
    'email': 'testuser@example.com',
    'name': 'Test User',
    'sub': '1234567890',
}


@pytest.mark.django_db
def test_google_login_new_user():
    client = APIClient()
    with patch('accounts.views.id_token.verify_oauth2_token', return_value=VALID_IDINFO):
        response = client.post(GOOGLE_ENDPOINT, {'id_token': 'fake-token'}, format='json')

    assert response.status_code == 200
    assert 'access' in response.data
    assert 'refresh' in response.data
    assert User.objects.filter(email=VALID_IDINFO['email']).exists()


@pytest.mark.django_db
def test_google_login_existing_credential_user():
    client = APIClient()
    client.post(
        '/api/auth/register/',
        {
            'username': 'existinguser',
            'email': VALID_IDINFO['email'],
            'password': 'StrongPass123!',
            'password2': 'StrongPass123!',
        },
        format='json',
    )
    assert User.objects.filter(email=VALID_IDINFO['email']).count() == 1

    with patch('accounts.views.id_token.verify_oauth2_token', return_value=VALID_IDINFO):
        response = client.post(GOOGLE_ENDPOINT, {'id_token': 'fake-token'}, format='json')

    assert response.status_code == 200
    assert 'access' in response.data
    assert 'refresh' in response.data
    assert User.objects.filter(email=VALID_IDINFO['email']).count() == 1


@pytest.mark.django_db
def test_google_login_invalid_token():
    client = APIClient()
    with patch(
        'accounts.views.id_token.verify_oauth2_token',
        side_effect=GoogleAuthError('bad token'),
    ):
        response = client.post(GOOGLE_ENDPOINT, {'id_token': 'bad-token'}, format='json')

    assert response.status_code == 401
    assert response.data['detail'] == 'Invalid or expired Google token.'


@pytest.mark.django_db
def test_google_login_missing_token():
    client = APIClient()
    response = client.post(GOOGLE_ENDPOINT, {}, format='json')

    assert response.status_code == 400
    assert 'detail' in response.data


@pytest.mark.django_db
def test_google_login_unconfigured():
    client = APIClient()
    with override_settings(GOOGLE_OAUTH_CLIENT_ID=''):
        response = client.post(GOOGLE_ENDPOINT, {'id_token': 'any-token'}, format='json')

    assert response.status_code == 503
    assert response.data['detail'] == 'Google OAuth is not configured.'
