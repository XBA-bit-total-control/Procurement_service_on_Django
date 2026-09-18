"""Создание приложения Celery.

Для конфигурации используются настройки из settings.py
"""

import os

from celery import Celery


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'purchasing_service.settings')

celery_app = Celery('purchasing_service')
celery_app.config_from_object('django.conf:settings', namespace='CELERY')
celery_app.autodiscover_tasks()
