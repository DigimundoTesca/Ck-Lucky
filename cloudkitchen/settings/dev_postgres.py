from cloudkitchen.settings.dev import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.getenv('LUCKY_DB_NAME'),
        'USER': os.getenv('LUCKY_DB_USER'),
        'PASSWORD': os.getenv('LUCKY_DB_PASSWORD'),
        'HOST': os.getenv('LUCKY_DB_HOST'),
        'PORT': os.getenv('LUCKY_DB_PORT'),
    }
}
