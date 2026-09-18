from django.dispatch import receiver
from django_rest_passwordreset.signals import reset_password_token_created

from .data.body_of_letters import reset_password
from .tasks import send_email


@receiver(reset_password_token_created)
def email_about_password_change(reset_password_token, *args, **kwargs):
    """Обработчик сигналов для django_rest_passwordreset.

    Направляет задачу Celery для отправки письма с токеном для сброса пароля.
    """
    email = reset_password_token.user.email
    first_name = reset_password_token.user.first_name
    token = reset_password_token.key

    send_email.delay(
        subject="Compraretis service: Password reset",
        recipient=email,
        content=reset_password(first_name, token)
    )
