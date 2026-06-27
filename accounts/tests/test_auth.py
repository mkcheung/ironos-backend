import pytest
from rest_framework.test import APIClient


REGISTER_URL = '/api/auth/register/'
TOKEN_URL = '/api/auth/token/'
REFRESH_URL = '/api/auth/token/refresh/'
LOGOUT_URL = '/api/auth/logout/'
ME_URL = '/api/auth/me/'


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def registered_user(api_client):
    """Register a user and return the response data (access, refresh, user)."""
    payload = {
        'username': 'testuser',
        'email': 'testuser@example.com',
        'password': 'StrongPass123!',
        'password2': 'StrongPass123!',
    }
    response = api_client.post(REGISTER_URL, payload, format='json')
    assert response.status_code == 201
    return response.data


@pytest.mark.django_db
def test_register(api_client):
    payload = {
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'StrongPass123!',
        'password2': 'StrongPass123!',
    }
    response = api_client.post(REGISTER_URL, payload, format='json')
    assert response.status_code == 201
    data = response.data
    assert 'access' in data
    assert 'refresh' in data
    assert 'user' in data
    assert data['user']['username'] == 'newuser'
    assert data['user']['email'] == 'newuser@example.com'
    # Password must NOT be in the response
    assert 'password' not in data['user']


@pytest.mark.django_db
def test_register_password_mismatch(api_client):
    payload = {
        'username': 'mismatchuser',
        'email': 'mismatch@example.com',
        'password': 'StrongPass123!',
        'password2': 'DifferentPass456!',
    }
    response = api_client.post(REGISTER_URL, payload, format='json')
    assert response.status_code == 400


@pytest.mark.django_db
def test_login(api_client, registered_user):
    payload = {
        'username': 'testuser',
        'password': 'StrongPass123!',
    }
    response = api_client.post(TOKEN_URL, payload, format='json')
    assert response.status_code == 200
    data = response.data
    assert 'access' in data
    assert 'refresh' in data


@pytest.mark.django_db
def test_refresh(api_client, registered_user):
    refresh_token = registered_user['refresh']
    response = api_client.post(REFRESH_URL, {'refresh': refresh_token}, format='json')
    assert response.status_code == 200
    data = response.data
    assert 'access' in data


@pytest.mark.django_db
def test_me(api_client, registered_user):
    access_token = registered_user['access']
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
    response = api_client.get(ME_URL)
    assert response.status_code == 200
    data = response.data
    assert data['username'] == 'testuser'
    assert data['email'] == 'testuser@example.com'
    assert 'profile' in data


@pytest.mark.django_db
def test_logout(api_client, registered_user):
    access_token = registered_user['access']
    refresh_token = registered_user['refresh']
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
    response = api_client.post(LOGOUT_URL, {'refresh': refresh_token}, format='json')
    assert response.status_code == 200


@pytest.mark.django_db
def test_blacklisted_token_rejected(api_client, registered_user):
    access_token = registered_user['access']
    refresh_token = registered_user['refresh']

    # Logout to blacklist the refresh token
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
    logout_response = api_client.post(LOGOUT_URL, {'refresh': refresh_token}, format='json')
    assert logout_response.status_code == 200

    # Try to use the now-blacklisted refresh token
    api_client.credentials()
    response = api_client.post(REFRESH_URL, {'refresh': refresh_token}, format='json')
    assert response.status_code == 401
