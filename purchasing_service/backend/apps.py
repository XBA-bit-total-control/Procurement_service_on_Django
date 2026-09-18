from django.apps import AppConfig


class BackendConfig(AppConfig):
    """Конфигурация приложения Backend.

    Задает настройки приложения и подключает сигналы.

    Attributes:
        default_auto_field: тип автоинкрементного поля для моделей
        name: название приложения
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'backend'

    def ready(self):
        """Инициализация приложения.

        Подключает модуль signals для обработки сигналов.
        """
        from . import signals
