from pathlib import Path
import os
from dotenv import load_dotenv



# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv()

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-__=g*pnp%=$xt58=gqsipqfp&@dr105ils$gq6-td(p(!28bf='

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["127.0.0.1", "191.252.182.151", "localhost", "apicota.com.br", "www.apicota.com.br"]

CSRF_TRUSTED_ORIGINS = ["https://apicota.com.br", "https://www.apicota.com.br"]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.intranet',
    'apps.indices',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.intranet.context_processors.navbar_links',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', os.environ.get('REPORTING_DB_NAME', 'nome_do_banco')),
        'USER': os.environ.get('DB_USER', os.environ.get('REPORTING_DB_USER', 'usuario')),
        'PASSWORD': os.environ.get('DB_PASSWORD', os.environ.get('REPORTING_DB_PASSWORD', 'senha')),
        'HOST': os.environ.get('DB_HOST', os.environ.get('REPORTING_DB_HOST', 'localhost')),
        'PORT': os.environ.get('DB_PORT', os.environ.get('REPORTING_DB_PORT', '5432')),
    },
    'reporting': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('REPORTING_DB_NAME', 'nome_do_banco'),
        'USER': os.environ.get('REPORTING_DB_USER', 'usuario'),
        'PASSWORD': os.environ.get('REPORTING_DB_PASSWORD', 'senha'),
        'HOST': os.environ.get('REPORTING_DB_HOST', 'localhost'),
        'PORT': os.environ.get('REPORTING_DB_PORT', '5432'),
    },
}



# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
MEDIA_URL = '/media/'

STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_ROOT  = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'intranet_home'
LOGOUT_REDIRECT_URL = 'login'
