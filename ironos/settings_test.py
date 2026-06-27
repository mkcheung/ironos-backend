from .settings import *  # noqa

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Exclude core (pgvector) and celery beat (no need for tests)
INSTALLED_APPS = [app for app in INSTALLED_APPS if app not in ('core', 'django_celery_beat')]

# Provide a dummy client ID so the Google OAuth guard doesn't block tests.
# Individual tests that need to test the unconfigured path use override_settings.
GOOGLE_OAUTH_CLIENT_ID = 'test-client-id.apps.googleusercontent.com'
