# coding: utf8
"""
Django settings for django project.

Generated by 'django-admin startproject' using Django 1.8.7.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""
from __future__ import absolute_import
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 管理员邮箱
ADMINS = (
    ('admin', 'dkluohangb@163.com'),
)

# Email设置
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# 邮箱SMTP服务器(邮箱需要开通SMTP服务)
EMAIL_HOST = 'smtp.163.com'
# 邮箱SMTP服务端口
EMAIL_PORT = 25
# 发件邮箱帐号
EMAIL_HOST_USER = 'wzdexian2016@163.com'
# 授权码
EMAIL_HOST_PASSWORD = '12345678lh'
# 为邮件标题的前缀,默认是'[django]'
EMAIL_SUBJECT_PREFIX = '[告警]'
# 开启安全链接
EMAIL_USE_TLS = False
# 设置发件人
DEFAULT_FROM_EMAIL = SERVER_EMAIL = EMAIL_HOST_USER

# django-celery
import djcelery
import config

djcelery.setup_loader()

BROKER_URL = 'redis://%s:%s/%s' % (config.REDIS_HOST, config.REDIS_PORT, config.REDIS_DB)
CELERY_ENABLE_UTC = False
CELERY_TASK_PUBLISH_RETRY_POLICY = {
    'max_retries': 1,
    'interval_start': 0,
    'interval_step': 0.2,
    'interval_max': 0.2,
}

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'xnn8hc^ef+l=)3cxqac-@d4m-ylph)u=g=97cis5c4-1%&06)^'

# SECURITY WARNING: don't run with debug turned on in production!
TEMPLATE_DEBUG = DEBUG = False

ALLOWED_HOSTS = ["*"]

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'app',
    'common',
    'background',
    'foreground',
    'pay',
    'djcelery',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    # 'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'django.middleware.security.SecurityMiddleware',
)

TEMPLATE_CONTEXT_PROCESSORS =(
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    "django.contrib.messages.context_processors.messages",
    "django.core.context_processors.request",
)

ROOT_URLCONF = 'mjango.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],  # 加上这个，不用每次带路径了
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'mjango.wsgi.application'
LOGIN_URL = '/account/login/'

# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',       # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'mahjong',                          # Or path to database file if using sqlite3.
        'USER': 'root',                             # Not used with sqlite3.
        'PASSWORD': '',                             # Not used with sqlite3.
        'HOST': '127.0.0.1',                        # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                                 # Set to empty string for default. Not used with sqlite3.
        'CONN_MAX_AGE': None,                       # 永不关闭
    },
    'other': {
        'ENGINE': 'django.db.backends.mysql',       # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'mahjong_other',                    # Or path to database file if using sqlite3.
        'USER': 'root',                             # Not used with sqlite3.
        'PASSWORD': '',                             # Not used with sqlite3.
        'HOST': '127.0.0.1',                        # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                                 # Set to empty string for default. Not used with sqlite3.
        'CONN_MAX_AGE': None,                       # 永不关闭
    },
}

# 数据库路由
DATABASE_ROUTERS = ['common.db_router.DBRouter']


# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'zh-CN'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_L10N = True

# 启用这个后各种navie datetime error就来了，烦
USE_TZ = False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/static/'

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'


LOG_FORMAT = '\n'.join((
    '/' + '-' * 80,
    '[%(levelname)s][%(asctime)s][%(process)d:%(thread)d][%(filename)s:%(lineno)d %(funcName)s]:',
    '%(message)s',
    '-' * 80 + '/',
))

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,

    'formatters': {
        'standard': {
            'format': LOG_FORMAT,
        },
    },

    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },
        'require_debug_true': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': lambda x: DEBUG,
        }
    },
    'handlers': {
        'django_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, "logs/django.log"),
            'maxBytes': 1024*1024*500,
            'backupCount': 5,
            'formatter': 'standard',
        },
        'console': {
            'level': 'DEBUG',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
        'mail_admins': {
            'level': 'ERROR',
            # 'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': False,
        },
        'main_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, "logs/main.log"),
            'maxBytes': 1024*1024*500,
            'backupCount': 5,
            'formatter': 'standard',
        },
        'sche_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, "logs/schedule.log"),
            'maxBytes': 1024*1024*500,
            'backupCount': 5,
            'formatter': 'standard',
        },
        'timer_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, "logs/timer.log"),
            'maxBytes': 1024*1024*500,
            'backupCount': 5,
            'formatter': 'standard',
        },
        'pay_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, "logs/pay.log"),
            'maxBytes': 1024*1024*500,
            'backupCount': 5,
            'formatter': 'standard',
        },
        'firefly_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, "logs/firefly.log"),
            'maxBytes': 1024*1024*500,
            'backupCount': 5,
            'formatter': 'standard',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['django_file', 'mail_admins'],
            'level': 'DEBUG',
            'propagate': False
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'main': {
            'handlers': ['main_file', 'console', 'mail_admins'],
            'level': 'DEBUG',
            'propagate': False
        },
        'schedule': {
            'handlers': ['sche_file', 'console', 'mail_admins'],
            'level': 'DEBUG',
            'propagate': False
        },
        'timer': {
            'handlers': ['timer_file', 'console', 'mail_admins'],
            'level': 'DEBUG',
            'propagate': False
        },
        'pay': {
            'handlers': ['pay_file', 'console', 'mail_admins'],
            'level': 'DEBUG',
            'propagate': False
        },
        'firefly': {
            'handlers': ['firefly_file', 'mail_admins'],
            'level': 'DEBUG',
            'propagate': False
        },
    }
}