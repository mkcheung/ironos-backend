from .settings import *  # noqa

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Exclude core (pgvector) and celery beat (no need for tests)
INSTALLED_APPS = [app for app in INSTALLED_APPS if app not in ('core', 'django_celery_beat')]
